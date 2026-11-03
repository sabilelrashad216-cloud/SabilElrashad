def publish_item(item, services):
    return [{'service': s, 'skipped': 'Buffer connector handled by Manus publishing workflow'} for s in services]
