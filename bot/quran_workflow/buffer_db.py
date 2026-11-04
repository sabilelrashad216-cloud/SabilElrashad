import json
import os
import urllib.request

API = 'https://api.buffer.com'
CHANNELS = {
    'facebook': os.environ.get('BUFFER_FACEBOOK_CHANNEL_ID', '6aea2c28e29c69a1714ef322'),
    'tiktok': os.environ.get('BUFFER_TIKTOK_CHANNEL_ID', '6aea2c4fe29c69a1714ef847'),
    'youtube': os.environ.get('BUFFER_YOUTUBE_CHANNEL_ID', '6aea2715e29c69a1714e823d'),
}


def _graphql(query):
    token = os.environ.get('BUFFER_API_KEY', '')
    if not token:
        raise RuntimeError('BUFFER_API_KEY غير مضبوط')
    req = urllib.request.Request(API, data=json.dumps({'query': query}, ensure_ascii=False).encode(), method='POST', headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as response:
        result = json.loads(response.read().decode())
    if result.get('errors'):
        raise RuntimeError(result['errors'])
    return result.get('data', {}).get('createPost', {})


def create_image_post(service, text, image_url, mode='addToQueue', due_at=None):
    channel_id = CHANNELS[service]
    fields = [f'channelId: "{channel_id}"', 'schedulingType: automatic', f'mode: {mode}', f'text: {json.dumps(text, ensure_ascii=False)}', f'assets: [{{image: {{url: {json.dumps(image_url)}, metadata: {{altText: "سبيل الرشاد"}}}}}}]']
    if due_at:
        fields.append(f'dueAt: "{due_at}"')
    if service == 'facebook':
        fields.append('metadata: {facebook: {type: post}}')
    elif service == 'tiktok':
        fields.append('metadata: {tiktok: {title: "سبيل الرشاد"}}')
    query = 'mutation Publish { createPost(input: {' + ', '.join(fields) + '}) { ... on PostActionSuccess { post { id status dueAt } } ... on MutationError { message } } }'
    result = _graphql(query)
    if result.get('message'):
        raise RuntimeError(result['message'])
    post = result.get('post')
    if not post or not post.get('id'):
        raise RuntimeError(f'Buffer لم يؤكد إنشاء المنشور: {result}')
    return post


def upload_public(path):
    import subprocess
    result = subprocess.run(['manus-upload-file', str(path)], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:] or result.stdout[-500:])
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith('http://') or line.startswith('https://'):
            return line
    raise RuntimeError('لم يعثر رفع الملف على رابط عام')


def make_vertical_video(image_path):
    import subprocess
    output = str(image_path).rsplit('.', 1)[0] + '_short.mp4'
    command = [
        'ffmpeg', '-y', '-loop', '1', '-i', str(image_path), '-t', '8',
        '-vf', 'scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1920:0:285:color=0x092d27,format=yuv420p',
        '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', output,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-800:])
    return output


def create_video_post(service, text, video_url, mode='addToQueue'):
    channel_id = CHANNELS[service]
    fields = [f'channelId: "{channel_id}"', 'schedulingType: automatic', f'mode: {mode}', f'text: {json.dumps(text, ensure_ascii=False)}', f'assets: [{{video: {{url: {json.dumps(video_url)}}}}}]']
    if service == 'facebook':
        fields.append('metadata: {facebook: {type: reel}}')
    elif service == 'tiktok':
        fields.append('metadata: {tiktok: {title: "سبيل الرشاد"}}')
    elif service == 'youtube':
        fields.append('metadata: {youtube: {title: "سبيل الرشاد | محتوى إسلامي", categoryId: "22", privacy: public, notifySubscribers: true, madeForKids: false}}')
    query = 'mutation PublishVideo { createPost(input: {' + ', '.join(fields) + '}) { ... on PostActionSuccess { post { id status dueAt } } ... on MutationError { message } } }'
    result = _graphql(query)
    if result.get('message'):
        raise RuntimeError(result['message'])
    post = result.get('post')
    if not post or not post.get('id'):
        raise RuntimeError(f'Buffer لم يؤكد إنشاء فيديو {service}: {result}')
    return post


def publish_image_item(item, image_path, services, mode='addToQueue'):
    text = item.get('main_text') or ''
    image_url = upload_public(image_path)
    results = []
    for service in services:
        if service == 'youtube':
            results.append({'service': service, 'skipped': 'YouTube يحتاج فيديو Shorts وليس صورة'})
            continue
        results.append({'service': service, 'post': create_image_post(service, text, image_url, mode=mode)})
    return image_url, results


def publish_media_item(item, image_path, mode='addToQueue'):
    text = item.get('main_text') or ''
    image_url = upload_public(image_path)
    video_path = make_vertical_video(image_path)
    video_url = upload_public(video_path)
    results = [
        {'service': 'facebook post', 'post': create_image_post('facebook', text, image_url, mode=mode)},
        {'service': 'facebook reel', 'post': create_video_post('facebook', text, video_url, mode=mode)},
        {'service': 'tiktok', 'post': create_video_post('tiktok', text, video_url, mode=mode)},
        {'service': 'youtube shorts', 'post': create_video_post('youtube', text, video_url, mode=mode)},
    ]
    return image_url, video_url, results
