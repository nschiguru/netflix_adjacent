import json
import boto3
from decimal import Decimal
import os
from botocore.exceptions import ClientError
import uuid

# AWS Clients
s3_client = boto3.client('s3')
polly_client = boto3.client('polly')
dynamodb = boto3.resource('dynamodb')
iam_client = boto3.client('iam')
sns_client = boto3.client('sns')

# Configuration - UPDATE THESE VALUES
BUCKET_NAME = 'netflix-clone-videos-nschiguru'
USER_UPLOADS_BUCKET = 'netflix-clone-user-uploads-nschiguru'  # UPDATE THIS
CLOUDFRONT_DOMAIN = 'd14amx5ccbkpyp.cloudfront.net'  # UPDATE THIS (videos)
CLOUDFRONT_UPLOADS_DOMAIN = 'diw0z33w7mkwx.cloudfront.net'  # UPDATE THIS (uploads)
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:801691344221:netflix-video-upload-notifications'  # UPDATE THIS

# DynamoDB Tables
progress_table = dynamodb.Table('NetflixUserData')
metadata_table = dynamodb.Table('NetflixVideoMetadata')

def lambda_handler(event, context):
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    # Handle OPTIONS for CORS
    http_method = event.get('requestContext', {}).get('http', {}).get('method')
    if not http_method:
        http_method = event.get('httpMethod', '')
    
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers, 'body': ''}
    
    try:
        print("Received event:", json.dumps(event))
        
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except:
                body = {}
        
        print("Parsed body:", json.dumps(body))
        action = body.get('action')
        print("Action:", action)
        
        # Route actions
        if action == 'authenticate':
            return authenticate_user(body, cors_headers)
        elif action == 'getVideo':
            return get_video_url(body, cors_headers)
        elif action == 'saveProgress':
            return save_user_progress(body, cors_headers)
        elif action == 'getProgress':
            return get_user_progress(body, cors_headers)
        elif action == 'tts':
            return generate_tts_audio(body, cors_headers)
        elif action == 'requestUploadUrl':
            return request_upload_url(body, cors_headers)
        elif action == 'listUserMovies':
            return list_user_movies(body, cors_headers)
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Invalid action: {action}'})
            }
    except Exception as e:
        print("Error:", str(e))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }

def authenticate_user(body, cors_headers):
    """Authenticate user via IAM"""
    username = body.get('username')
    access_key = body.get('accessKey')
    
    if not username or not access_key:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Username and access key required'})
        }
    
    try:
        user = iam_client.get_user(UserName=username)
        user_policies = iam_client.list_attached_user_policies(UserName=username)
        
        has_netflix_access = False
        for policy in user_policies['AttachedPolicies']:
            if 'Netflix' in policy['PolicyName']:
                has_netflix_access = True
                break
        
        if not has_netflix_access:
            inline_policies = iam_client.list_user_policies(UserName=username)
            for policy_name in inline_policies['PolicyNames']:
                if 'Netflix' in policy_name:
                    has_netflix_access = True
                    break
        
        if not has_netflix_access:
            groups = iam_client.list_groups_for_user(UserName=username)
            for group in groups['Groups']:
                group_policies = iam_client.list_attached_group_policies(GroupName=group['GroupName'])
                for policy in group_policies['AttachedPolicies']:
                    if 'Netflix' in policy['PolicyName']:
                        has_netflix_access = True
                        break
        
        if not has_netflix_access:
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({
                    'authenticated': False,
                    'error': 'User does not have Netflix access privileges'
                })
            }
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'authenticated': True,
                'username': username,
                'userId': user['User']['UserId']
            })
        }
        
    except iam_client.exceptions.NoSuchEntityException:
        return {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'authenticated': False, 'error': 'User not found'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'authenticated': False, 'error': str(e)})
        }

def get_video_url(body, cors_headers):
    """Get video URL via CloudFront"""
    movie_id = body.get('movieId')
    
    if not movie_id:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'movieId required'})
        }
    
    # Use CloudFront URL instead of direct S3
    video_url = f"https://{CLOUDFRONT_DOMAIN}/{movie_id}.mp4"
    
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({'videoUrl': video_url, 'movieId': movie_id})
    }

def save_user_progress(body, cors_headers):
    """Save user watch progress"""
    user_id = body.get('userId')
    movie_id = body.get('movieId')
    progress = body.get('progress')
    
    if not all([user_id, movie_id, progress is not None]):
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'userId, movieId, progress required'})
        }
    
    progress_table.put_item(
        Item={
            'userId': user_id,
            'movieId': movie_id,
            'watchProgress': Decimal(str(progress)),
            'lastWatched': body.get('timestamp', 'unknown')
        }
    )
    
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({'message': 'Progress saved'})
    }

def get_user_progress(body, cors_headers):
    """Get user watch progress"""
    user_id = body.get('userId')
    movie_id = body.get('movieId')
    
    if not all([user_id, movie_id]):
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'userId, movieId required'})
        }
    
    response = progress_table.get_item(
        Key={'userId': user_id, 'movieId': movie_id}
    )
    
    item = response.get('Item', {})
    if 'watchProgress' in item:
        item['watchProgress'] = float(item['watchProgress'])
    
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps(item if item else {'watchProgress': 0})
    }

def generate_tts_audio(body, cors_headers):
    """Generate TTS audio using Polly"""
    text = body.get('text')
    
    if not text:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'text required'})
        }
    
    try:
        # Generate audio with Polly
        polly_response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Joanna'
        )
        
        audio_bytes = polly_response['AudioStream'].read()
        tts_key = f"tts/{uuid.uuid4()}.mp3"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=tts_key,
            Body=audio_bytes,
            ContentType='audio/mpeg'
        )
        
        # Return CloudFront URL
        audio_url = f"https://{CLOUDFRONT_DOMAIN}/{tts_key}"
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'audioUrl': audio_url})
        }
    except Exception as e:
        print("Polly error:", e)
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }

def request_upload_url(body, cors_headers):
    """Generate presigned URL for user upload"""
    user_id = body.get('userId')
    file_name = body.get('fileName')
    
    if not user_id or not file_name:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'userId, fileName required'})
        }
    
    # Generate unique video ID
    video_id = f"{user_id}/{uuid.uuid4()}-{file_name}"
    
    # Generate presigned upload URL
    upload_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': USER_UPLOADS_BUCKET,
            'Key': video_id,
            'ContentType': 'video/mp4'
        },
        ExpiresIn=3600
    )
    
    # Save metadata to DynamoDB
    try:
        metadata_table.put_item(
            Item={
                'videoId': video_id,
                'userId': user_id,
                'fileName': file_name,
                'uploadedAt': body.get('timestamp', 'unknown'),
                'status': 'uploaded'
            }
        )
    except Exception as e:
        print(f"Metadata save error: {e}")
    
    # Send SNS notification
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='New Video Upload',
            Message=f"User {user_id} uploaded: {file_name}"
        )
    except Exception as e:
        print(f"SNS error: {e}")
    
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({
            'uploadUrl': upload_url,
            'videoId': video_id
        })
    }

def list_user_movies(body, cors_headers):
    """List user's uploaded movies"""
    user_id = body.get('userId')
    
    if not user_id:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'userId required'})
        }
    
    try:
        # List objects in user's folder
        response = s3_client.list_objects_v2(
            Bucket=USER_UPLOADS_BUCKET,
            Prefix=f"{user_id}/"
        )
        
        movies = []
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                # Use CloudFront URL for uploads
                video_url = f"https://{CLOUDFRONT_UPLOADS_DOMAIN}/{key}"
                
                movies.append({
                    'movieId': key.split('/')[-1],
                    'videoUrl': video_url,
                    'uploadedAt': obj['LastModified'].isoformat()
                })
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'movies': movies})
        }
    except Exception as e:
        print(f"List error: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }