import os
import sys

import sqlalchemy.exc
from sqlalchemy import engine_from_config
from sqlalchemy_utils import (
    database_exists,
    create_database,
    drop_database
)

from models import (
    DBSession,
    Base,
)

from utils import (
    get_logger,
    yml_config_as_dict
)

logger = get_logger()


def usage_commandline(argv=None):
    if argv:
        cmd = os.path.basename(argv[0])
        logger.error('usage: %s <config_uri>\n'  # TODO optional dropall
                     '(example: "%s config.yml")' % (cmd, cmd))
    sys.exit(1)


def usage(message=None):
    if message:
        logger.error(message)

    sys.exit(1)


def drop_table(db, engine):
    logger.debug("TODO db_utils.drop_table")
    db.drop(bind=engine, checkfirst=True)


def drop_all_tables(engine):
    logger.debug("Dropping all tables from engine")
    Base.metadata.drop_all(bind=engine)


def init_databases(config_file='config.yml', drop_old=False):
    logger.debug(f"Initializing database from {config_file}, drop_old={drop_old}")
    # Set up a DB from config file
    config = yml_config_as_dict(config_file)

    engine = engine_from_config(config, 'sqlalchemy.')  # TODO DRY or overkill?

    db_preexists = database_exists(engine.url)
    logger.debug(f"Database {'already' if db_preexists else 'does not'} exist")

    if not db_preexists:
        create_database(engine.url)

    if drop_old and db_preexists:  # Drop database?
        logger.debug("Dropping databases...")
        try:
            drop_all_tables(engine)
        except sqlalchemy.exc.DatabaseError as e:
            logger.warning(f"Intialize DB Error:\n{type(e).__name__}: {str(e)}")
            logger.warning("Attempting to drop entire database.")
            drop_database(engine.url)
    elif not db_preexists:
        logger.warning(f"Not attempting to drop tables since it the database didn't exist beforehand.")

    DBSession.configure(bind=engine)

    try:
        logger.debug("Generating tables from Base.")
        Base.metadata.create_all(engine)
        logger.debug("Tables generated.")
    except sqlalchemy.exc.InternalError as e:
        usage(message=f"Intialize DB Error:\n{type(e).__name__}: {str(e)}")


def init_databases_commandline(argv=None):
    if argv is None:
        argv = sys.argv

    logger.debug(f"Initializing database from commandline with arguments {argv}")
    if len(argv) < 2:
        usage_commandline(argv=argv)

    config_uri = argv[1]
    drop_old = bool(len(argv) > 2)

    init_databases(config_file=config_uri, drop_old=drop_old)


def bind_database_session(config_file='config.yml'):
    logger.debug(f"Getting database session from {config_file}")
    config = yml_config_as_dict(config_file)

    engine = engine_from_config(config, 'sqlalchemy.')
    db_exists = database_exists(engine.url)

    logger.debug(f"Database {'' if db_exists else 'does not'} exists.")

    if db_exists:
        DBSession.configure(bind=engine)


if __name__ == '__main__':
    init_databases_commandline()
