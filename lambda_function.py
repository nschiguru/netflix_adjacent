import json
import boto3
from decimal import Decimal
import os
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
polly_client = boto3.client('polly')
dynamodb = boto3.resource('dynamodb')
iam_client = boto3.client('iam')
table = dynamodb.Table('NetflixUserData')
BUCKET_NAME = 'netflix-clone-videos-nschiguru'
TTS_BUCKET = BUCKET_NAME

def lambda_handler(event, context):
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    # Handle OPTIONS request for CORS preflight
    http_method = event.get('requestContext', {}).get('http', {}).get('method')
    if not http_method:
        http_method = event.get('httpMethod', '')
    
    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': ''
        }
    
    try:
        # Debug: print the entire event to see what we're receiving
        print("Received event:", json.dumps(event))
        
        # Parse the body - handle different formats
        body = event.get('body', '{}')
        
        # If body is a string, parse it
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except:
                body = {}
        
        print("Parsed body:", json.dumps(body))
        
        action = body.get('action')
        print("Action:", action)
        
        # Authentication endpoint
        if action == 'authenticate':
            return authenticate_user(body, cors_headers)
        
        # For all other actions, verify the user has authenticated
        # In production, you'd validate a JWT token here
        
        if action == 'getVideo':
            return get_video_url(body, cors_headers)
        elif action == 'saveProgress':
            return save_user_progress(body, cors_headers)
        elif action == 'getProgress':
            return get_user_progress(body, cors_headers)
        elif action == 'textToSpeech':
            return generate_tts_audio(body, cors_headers)
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
    """
    Authenticate user by checking if they exist in IAM and have the required policy
    """
    username = body.get('username')
    access_key = body.get('accessKey')
    
    if not username or not access_key:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Username and access key are required'})
        }
    
    try:
        # Check if user exists in IAM
        user = iam_client.get_user(UserName=username)
        
        # Check if user has the required policy (NetflixAccessPolicy)
        user_policies = iam_client.list_attached_user_policies(UserName=username)
        
        has_netflix_access = False
        for policy in user_policies['AttachedPolicies']:
            if 'Netflix' in policy['PolicyName']:
                has_netflix_access = True
                break
        
        # Also check inline policies
        if not has_netflix_access:
            inline_policies = iam_client.list_user_policies(UserName=username)
            for policy_name in inline_policies['PolicyNames']:
                if 'Netflix' in policy_name:
                    has_netflix_access = True
                    break
        
        # Check group policies
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
        
        # User is authenticated and authorized
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
            'body': json.dumps({
                'authenticated': False,
                'error': 'User not found in IAM'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'authenticated': False,
                'error': f'Authentication error: {str(e)}'
            })
        }

def get_video_url(body, cors_headers):
    movie_id = body.get('movieId')
    
    if not movie_id:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'movieId is required'})
        }
    
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': f'{movie_id}.mp4'
        },
        ExpiresIn=3600
    )
    
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({
            'videoUrl': presigned_url,
            'movieId': movie_id
        })
    }

def save_user_progress(body, cors_headers):
    user_id = body.get('userId')
    movie_id = body.get('movieId')
    progress = body.get('progress')
    
    if not all([user_id, movie_id, progress is not None]):
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'userId, movieId, and progress are required'})
        }
    
    response = table.put_item(
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
        'body': json.dumps({'message': 'Progress saved successfully'})
    }

def get_user_progress(body, cors_headers):
    user_id = body.get('userId')
    movie_id = body.get('movieId')
    
    if not all([user_id, movie_id]):
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'userId and movieId are required'})
        }
    
    response = table.get_item(
        Key={
            'userId': user_id,
            'movieId': movie_id
        }
    )
    
    item = response.get('Item', {})
    
    # Convert Decimal to float for JSON serialization
    if 'watchProgress' in item:
        item['watchProgress'] = float(item['watchProgress'])
    
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps(item if item else {'watchProgress': 0})
    }


def generate_tts_audio(body, cors_headers):
    text = body.get('text')
    movie_id = body.get('movieId')

    if not text or not movie_id:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'text and movieId are required'})
        }

    try:
        # Generate audio with AWS Polly
        polly_response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Joanna'  # change if you want
        )

        audio_bytes = polly_response['AudioStream'].read()
        tts_key = f"tts/{movie_id}.mp3"

        # Upload MP3 to S3
        s3_client.put_object(
            Bucket=TTS_BUCKET,
            Key=tts_key,
            Body=audio_bytes,
            ContentType='audio/mpeg'
        )

        # Create presigned URL
        audio_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': TTS_BUCKET, 'Key': tts_key},
            ExpiresIn=3600
        )

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