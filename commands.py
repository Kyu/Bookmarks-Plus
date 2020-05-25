import re

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import UnboundExecutionError

from models import (
    DBSession,
    Base,
    Category,
    Note,
    User,
    Tweet
)

from utils import get_logger

logger = get_logger()


def find_db_object(obj, multiple_expected=False, **search_for):
    # type: (Base, bool, dict) -> Base
    logger.debug(f"Finding {obj}, searching for {search_for}, multiple_expected={multiple_expected}")
    try:
        if multiple_expected:
            prospective_obj = DBSession.query(obj).filter_by(**search_for).all()
        else:
            prospective_obj = DBSession.query(obj).filter_by(**search_for).one()
    except NoResultFound:
        logger.debug("No results found.")
        # If username not found
        prospective_obj = None
    else:
        logger.debug("Results found.")
    # TODO except MultipleResult if multiple_expected then ????
    # TODO small TODO bug, if a file is selected in project tab then it's show in "Current File Tab",
    # even if it's not the current visible file

    # TODO If User hasn't been updated in x Days, update 
    return prospective_obj


def create_db_object(obj, search_for=None, **kwargs):
    # type: (Base, dict, dict) -> Base
    new_obj = None

    if search_for:
        new_obj = find_db_object(obj, **search_for)
        # print(f"searching for {obj}: {search_for}\n{bool(new_obj)}")

    if not new_obj:
        # print(f"Creating new {obj}")
        new_obj = obj(**kwargs)
        DBSession.add(new_obj)
        DBSession.commit()

    return new_obj


def find_note_command(message):
    # type: (dict) -> list
    author_id = message.get('from')
    hashtags = message.get('hashtags')
    mentioned_ids = message.get('mentions')

    logger.debug(f"Finding notes from {author_id} with hashtags and mentions: {hashtags} and {mentioned_ids}")

    categories = []

    if hashtags:
        for h in hashtags:
            h_name = f"#{h}"
            search_for = dict(name=h_name, created_by_id=author_id)
            categories.append(find_db_object(Category, **search_for))

    if mentioned_ids:
        for m in mentioned_ids:
            search_for = dict(name=str(m), created_by_id=author_id)
            categories.append(find_db_object(Category, **search_for))

    notes = []
    # If categories is full of None or empty
    if (categories == [None] * len(categories)) or not categories:
        logger.debug(f"No preexisting categories (hashtags or mentions) were found")
        return ["0 notes found under those categories."]
    else:
        for i in categories:
            if i:
                # Album.query.join(Artist).join(Genre).filter(Genre.id==YOUR_GENRE_ID).all()
                # Dish.query.filter(Dish.restaurants.any(name=name)).all()
                # Artist.query.filter(Artist.albums.any(genre_id=genre.id)).all()
                # TODO many to many query
                notes_found = DBSession.query(Note).filter(Note.categories.any(name=i.name)).all()
                notes.extend(notes_found)
    number_found = f"{len(notes)} notes found under those categories."

    logger.debug(number_found+"\n")
    result = [number_found]
    count = 1
    for nt in notes:
        note_result = f"Note {count}:\n{nt.text}\n"
        count += 1
        result.append(note_result)

    return result


# TODO rename to create_note_command
# TODO create find_note_command, process_command_from_message
def create_note_command(message):
    # type: (dict) -> list
    # Check if user exists, create or update user
    # TODO duplicates??
    author_id = message.get('from')
    author = create_db_object(User, search_for={'id': author_id}, id=author_id)

    # Check if category by user exists, create if not
    category_names = message.get('hashtags', [])
    categories = list()
    for cn in category_names:
        cn_name = f"#{cn}"
        search_criteria = dict(name=cn_name, created_by_id=author.id)
        cat = create_db_object(Category, search_for=search_criteria, name=cn_name, created_by_id=author.id)
        if cat:
            categories.append(cat)
        else:
            logger.warning("Could not create cat???")

    mentioned_users_ids = message.get('mentions', [])

    for mu in mentioned_users_ids:
        search_criteria = dict(name=str(mu), created_by_id=author.id)
        cat = create_db_object(Category, search_for=search_criteria, name=mu, created_by_id=author.id)
        if cat:
            categories.append(cat)
        else:  # TODO DRY
            logger.warning("Could not create cat???")

    is_tweet = False
    urls = message.get('urls', {})
    tweet_links = list()
    tweets = list()

    twitter_status_regex = r'twitter\.com\/\w{3,15}\/status\/\d{2,25}'

    # Check if is tweet
    for link in urls.values():
        domain_args = re.search(twitter_status_regex, link)
        if domain_args:
            tweet_links.append(f"https://{domain_args.group()}")

    for tw in tweet_links:
        tw_url = tw.split("/")
        tw_id = int(tw_url[5])
        tweets.append(create_db_object(Tweet, search_for={'id': tw_id}, id=tw_id, url=tw))  # TODO Time epoch, **kwargs
        # TODO Get tweet author, create category based on tweet author ID
        # create new Tweet db object, screenshot

    attachment = message.get('attachment')
    # Download att

    text = message.get('text')  # TODO REMOVE SHORTLINKS
    all_short_links = []
    # TODO Shorten
    all_short_links.extend(mentioned_users_ids)
    all_short_links.extend(list(urls.keys()))
    all_short_links.extend(categories)
    all_short_links.append(attachment.get('short_url'))
    # TODO for i in all_short_links text.remove links?

    if text is not None and text in all_short_links:  # Doesn't remove media short url
        if text in list(urls.keys()):
            is_tweet = True
        # If text is just a url
        text = ""
    elif text is None:
        text = ""

    note = create_db_object(Note, text=text, created_by_id=author_id, is_tweet=is_tweet)

    if tweets:
        for t in tweets:
            note.tweets.append(t)
        DBSession.commit()

    if categories:
        for ct in categories:
            note.categories.append(ct)
        DBSession.commit()

    logger.debug(f"Parsed: {message['id']}\n{note.__dict__}")
    return ["Note created!"]


def process_command_from_message(message):
    # type: (dict) -> list
    logger.debug(f"Processing command from message id={message.get('id')}")
    # If url or attachment is present, its a create note
    write = bool(message.get('urls') or message.get('attachment'))
    result = None
    try:
        if write:
            logger.debug("Message is a write request.")
            result = create_note_command(message)
        else:
            logger.debug("Message is a read request.")
            result = find_note_command(message)
    except UnboundExecutionError as e:
        logger.error("Database does not exist or is not binded to engine!")
        logger.error(f"{type(e).__name__}: {str(e)}")

    return result
