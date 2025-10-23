import json
import boto3
from decimal import Decimal
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('NetflixUserData')

BUCKET_NAME = 'netflix-clone-videos-nschiguru'

def lambda_handler(event, context):
    try:
        action = event.get('action')
        
        if action == 'getVideo':
            return get_video_url(event)
        elif action == 'saveProgress':
            return save_user_progress(event)
        elif action == 'getProgress':
            return get_user_progress(event)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid action'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_video_url(event):
    movie_id = event.get('movieId')
    
    if not movie_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'movieId is required'})
        }
    
    # Generate presigned URL (valid for 1 hour)
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
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'videoUrl': presigned_url,
            'movieId': movie_id
        })
    }

def save_user_progress(event):
    user_id = event.get('userId')
    movie_id = event.get('movieId')
    progress = event.get('progress')
    
    if not all([user_id, movie_id, progress is not None]):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'userId, movieId, and progress are required'})
        }
    
    response = table.put_item(
        Item={
            'userId': user_id,
            'movieId': movie_id,
            'watchProgress': Decimal(str(progress)),
            'lastWatched': event.get('timestamp', 'unknown')
        }
    )
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': 'Progress saved successfully'})
    }

def get_user_progress(event):
    user_id = event.get('userId')
    movie_id = event.get('movieId')
    
    if not all([user_id, movie_id]):
        return {
            'statusCode': 400,
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
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(item if item else {'watchProgress': 0})
    }