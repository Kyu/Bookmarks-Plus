import time

from twitter.error import TwitterError

from parse_messages import parse_message
from commands import process_command_from_message
from database_utils import bind_database_session

from utils import (
    get_twitter_api,
    get_logger,
    NewMessageStates
)

logger = get_logger()

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = "%H-%M-%S"


MESSAGE_REQUEST_COUNT = 50
SLEEP_TIME = 90


twitter_api = get_twitter_api(config_file='config.yml')
bind_database_session()

self_id = twitter_api._access_token_key.split("-")[0]


def backup_last_dm(dm_id):
    # type: (int) -> None
    with open("last_dm.id", 'w') as dm:
        dm.write(str(dm_id))


def get_last_dm_id():
    # type: () -> int
    _id = -1
    try:
        with open("last_dm.id", 'r') as dm:
            lines = dm.readlines()
            if lines:
                _id = int(lines[0])
    except FileNotFoundError:
        pass

    return _id


highest_id_seen = get_last_dm_id()
last_id_parsed = highest_id_seen


def send_message_to_user(_id, text_list):
    # type: (int, list) -> None

    logger.debug(f"ID: {_id}, text_list: {text_list}")
    if not text_list:
        logger.error(f"Message not sent")
        twitter_api.PostDirectMessage(text="You should't be seeing this message.", user_id=_id)
    else:
        text = ""
        sent_count = 0
        for txt in text_list:
            if sent_count > 4:
                twitter_api.PostDirectMessage(text="Too many message send attempts!", user_id=_id)
            elif len(text) + len(txt) > 10000:
                twitter_api.PostDirectMessage(text=text, user_id=_id)
                text = txt
                sent_count += 1
            else:
                text += txt
        twitter_api.PostDirectMessage(text=text, user_id=_id)


def first_last_message_id(latest_dms):
    # type: (dict) -> tuple
    num_of_messages = len(latest_dms.get('events'))

    if num_of_messages:
        first_message_in_page_id = int(latest_dms.get('events')[0].get('id'))
        last_message_in_page_id = int(latest_dms.get('events')[num_of_messages - 1].get('id'))
    else:
        logger.debug(f"DM EVENTS EMPTY:\n{latest_dms}")
        first_message_in_page_id = last_message_in_page_id = -1

    return first_message_in_page_id, last_message_in_page_id


def are_new_messages(latest_dms, count=MESSAGE_REQUEST_COUNT):
    # type: (dict, int) -> NewMessageStates

    first_message_in_page_id, last_message_in_page_id = first_last_message_id(latest_dms)

    if last_message_in_page_id > highest_id_seen:
        if len(latest_dms.get('events')) < count:
            return NewMessageStates.CHECK_THIS_PAGE_ONLY
        return NewMessageStates.CHECK_NEXT_PAGE
    elif first_message_in_page_id > highest_id_seen:
        return NewMessageStates.CHECK_THIS_PAGE_ONLY
    else:
        return NewMessageStates.NO_NEW_MESSAGES


def get_latest_dms(return_json=True, count=MESSAGE_REQUEST_COUNT, next_cursor=None):
    # type: (bool, int, str) -> dict
    logger.debug(f"Getting messages, next_cursor={next_cursor}")
    try:
        latest_dms = twitter_api.GetDirectMessages(return_json=return_json, count=count, cursor=next_cursor)
    except TwitterError as e:
        error_code = e.message[0]['code']
        if error_code == 88:
            logger.error("DirectMessage.show rate limit Exceeded")
            latest_dms = dict(events=[], ratelimited=True)
        else:
            raise e

    logger.debug(f"Got {len(latest_dms.get('events'))} dms.")
    return latest_dms


def main():
    global last_id_parsed, highest_id_seen
    logger.debug("Getting DMs.")
    dms = []
    latest_dms = get_latest_dms()
    state = are_new_messages(latest_dms)

    while state in (NewMessageStates.CHECK_THIS_PAGE_ONLY, NewMessageStates.CHECK_NEXT_PAGE):
        dms.extend(latest_dms.get('events'))
        next_cursor = latest_dms.get('next_cursor')

        first_id, last_id = first_last_message_id(latest_dms)

        if first_id > last_id_parsed:
            last_id_parsed = first_id
        else:
            logger.debug(f"First ID({first_id}) < last_id_parsed({last_id_parsed})")

        if state == NewMessageStates.CHECK_NEXT_PAGE and next_cursor:
            latest_dms = get_latest_dms(next_cursor=next_cursor)  # try TwitterError.Code = 88 RateLimit
            state = are_new_messages(latest_dms)
        else:
            logger.debug(f"Logic failed: No new messages will be assessed. state={state}, next_cursor={next_cursor}")
            state = NewMessageStates.NO_NEW_MESSAGES

    logger.info("Processing DMs into commands.")
    for dm in reversed(dms):
        message = parse_message(dm)
        _from = message.get('from')
        if _from != self_id and message.get('id') > highest_id_seen:
            result = process_command_from_message(message)
            send_message_to_user(_from, result)

    if last_id_parsed > highest_id_seen:
        highest_id_seen = last_id_parsed
        backup_last_dm(highest_id_seen)

    logger.debug(f"Sleeping for {SLEEP_TIME}s.")
    time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    while True:
        main()

'''
for i in reversed(dms):
print(time.strftime(f"{DATE_FORMAT}-{TIME_FORMAT}", time.gmtime(time_sent)))
logger.info(f"Done {count}\nLastDm: {last_dm_sent_id}\nLoL: {len(dms)}\n")

time.sleep(60)
'''
