from enum import Enum
import logging
import logging.config
import yaml

import twitter


class NewMessageStates(Enum):
    NO_NEW_MESSAGES = 1
    CHECK_THIS_PAGE_ONLY = 2
    CHECK_NEXT_PAGE = 3


def yml_config_as_dict(config_name):
    # type: (str) -> dict
    with open(config_name, 'r') as cfg:
        config = yaml.safe_load(cfg.read())

    return config


def get_logger(config_file='logging.yml', logger_name='mainLogger'):
    # type: (str, str) -> logging.Logger
    config = yml_config_as_dict(config_file)

    logging.config.dictConfig(config)
    logger = logging.getLogger(logger_name)

    return logger


def get_twitter_api(config_file):
    # type: (str) -> twitter.Api
    logger = get_logger()

    config = yml_config_as_dict(config_file)

    consumer_key = config.get('consumer_key')
    consumer_secret = config.get('consumer_secret')
    access_token_key = config.get('access_token_key')
    access_token_secret = config.get('access_token_secret')

    twitter_api = twitter.Api(consumer_key=consumer_key,
                              consumer_secret=consumer_secret,
                              access_token_key=access_token_key,
                              access_token_secret=access_token_secret)

    verified = twitter_api.VerifyCredentials()
    if verified:
        logger.debug(f"Twitter verified as: {str(verified)}")
        return twitter_api
    else:
        logger.error("Could not verify twitter user, check info")
        return twitter.Api()
