from utils import get_logger
# TODO .get()
# TODO logs

logger = get_logger()


def save_anomalies(moly):
    # type: (object) -> None
    logger.warning(f"Anomaly detected! {moly}")

    with open("anomalies.json5", 'a+') as a:
        a.write(str(moly))


def get_messages(dm_data):
    # type: (dict) -> list

    # Takes dm data and returns events for parsing
    return dm_data['events']


def parse_events(events):
    # type: (list) -> list

    # Returns all {message_create} events, ignores rest
    count = len(events)
    anomalies = []
    proper_events = []

    for i in range(count):
        if events[i]['type'] in ("message_create",):
            proper_events.append(events[i])
        else:
            # TODO Yield an error on anomaly?
            anomalies.append(events[i])

    save_anomalies(anomalies)
    return proper_events


def parse_hashtags(hashtags):
    # type: (list) -> list

    # Get hashtag names
    tags = [i['text'] for i in hashtags]

    return tags


def parse_mentions(mentions):
    # type: (list) -> list

    # Get mentioned user ids
    ids = [i['id'] for i in mentions]

    return ids


def parse_urls(url_list):
    # type: (list) -> dict
    urls = dict()

    # Get full and short url
    for u in url_list:
        short_url = u.get('url')
        long_url = u.get('expanded_url')
        urls.update({short_url: long_url})

    return urls


def parse_attachments(att):
    # type: (dict) -> dict
    # TODO Check if works
    if not att:
        return dict()
    if att['type'] != 'media':
        save_anomalies(att)
        return dict()

    media = att['media']
    _id = media['id']
    short_url = media['url']
    _type = media['type']

    if _type == "photo":
        full_url = media['media_url_https']
    elif _type == "video":
        video_versions = media['video_info']['variants']

        bitrates = [i.get('bitrate', -1) for i in video_versions]
        highest_bitrate = max(bitrates)
        highest_bitrate_location = bitrates.index(highest_bitrate)

        full_url = video_versions[highest_bitrate_location]['url']

    else:
        save_anomalies(att)
        return dict()

    parsed_attachment = dict(id=_id, short_url=short_url, full_url=full_url)
    parsed_attachment['type'] = _type
    return parsed_attachment


def parse_message(message):
    # type: (dict) -> dict

    # Get message ID and timestamp
    _id = int(message['id'])
    timestamp_epoch_ms = message['created_timestamp']  # Milliseconds

    # Get sender and recipient
    to = message['message_create']['target']['recipient_id']
    _from = message['message_create']['sender_id']

    # Get message contents for parsing
    msg_data = message['message_create']['message_data']

    # Get text
    items = list(msg_data.keys())
    text = msg_data['text'] if "text" in items else ""

    # Get list of message entities
    entities = list(msg_data['entities'].keys())

    # Parse entities
    hashtags_raw = msg_data['entities']['hashtags'] if "hashtags" in entities else []
    mentions_raw = msg_data['entities']['user_mentions'] if "user_mentions" in entities else []
    urls_raw = msg_data['entities']['urls'] if "urls" in entities else []

    attachment_raw = msg_data['attachment'] if "attachment" in items else None

    hashtags = parse_hashtags(hashtags_raw)  # if none, pass
    mentions = parse_mentions(mentions_raw)
    urls = parse_urls(urls_raw)
    attachment = parse_attachments(attachment_raw)

    message = dict(id=_id, timestamp_epoch_ms=timestamp_epoch_ms, to=to, text=text, hashtags=hashtags,
                   mentions=mentions, urls=urls, attachment=attachment)
    message['from'] = _from

    return message
