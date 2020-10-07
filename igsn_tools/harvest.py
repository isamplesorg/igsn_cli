"""
Command line client for working with International Geo Sample Numbers (IGSNs).

Supported by NSF Award 2004815
"""
import sys
import logging
import datetime
import click
import dateparser
import igsn_lib.models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
LOG_FORMAT = "%(asctime)s %(name)s:%(levelname)s: %(message)s"


def getLogger():
    return logging.getLogger("igsn-harvest")


def getEngine(db_connection):
    engine = create_engine(db_connection)
    igsn_lib.models.createAll(engine)
    return engine


def getSession(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


@click.group()
@click.option(
    "-v",
    "--verbosity",
    default="WARNING",
    help="Specify logging level",
    show_default=True,
)
@click.option(
    "-d",
    "--db-connect",
    default="sqlite:///igsn_harvest.db",
    help="Database connection string",
    show_default=True,
)
@click.pass_context
def main(ctx, verbosity, db_connect):
    ctx.ensure_object(dict)
    verbosity = verbosity.upper()
    logging.basicConfig(
        level=LOG_LEVELS.get(verbosity, logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    L = getLogger()
    if verbosity not in LOG_LEVELS.keys():
        L.warning("%s is not a log level, set to INFO", verbosity)
    ctx.obj["engine"] = getEngine(db_connect)


@main.command()
@click.pass_context
def lists_services(ctx):
    session = getSession(ctx.obj["engine"])
    for service in session.query(igsn_lib.models.Service).all():
        print(service)
    session.close()


@main.command()
@click.pass_context
@click.argument("url", nargs=1)
def add_service(ctx, url):
    session = getSession(ctx.obj["engine"])
    service = igsn_lib.models.addService(session, url)
    print(service)
    session.close()


@main.command()
@click.pass_context
@click.option("-i", "--service-id", help="ID of service to use", default=1)
def list_service_sets(ctx, service_id):
    session = getSession(ctx.obj["engine"])
    for service in (
        session.query(igsn_lib.models.Service)
        .filter(igsn_lib.models.Service.id == service_id)
        .all()
    ):
        print(f"{service.url}")
        sets = service.listSets()
        for s in sets:
            print(f"  {s.setSpec} : {s.setName}")
    session.close()


@click.option("-i", "--service-id", help="ID of service for new job", default=1)
@click.option("-f", "--from-date", help="Starting date of harvest window", default=None)
@click.option("-t", "--to-date", help="Ending date of harvest window", default="now")
@click.option("-s", "--set-spec", help="Set specification to use", default=None)
@main.command()
@click.pass_context
def add_job(ctx, service_id, from_date, to_date, set_spec):
    L = getLogger()
    dfrom_date = None
    if from_date is not None:
        dfrom_date = dateparser.parse(from_date, settings={"TIMEZONE": "+0000"})
    dto_date = None
    if to_date is not None:
        dto_date = dateparser.parse(to_date, settings={"TIMEZONE": "+0000"})
    if dto_date < dfrom_date:
        L.error("from-date must be older than to-date")
        return 1
    session = getSession(ctx.obj["engine"])
    service = (
        session.query(igsn_lib.models.Service)
        .filter(igsn_lib.models.Service.id == service_id)
        .one()
    )
    service.createJob(
        session=session,
        ignore_deleted=False,
        metadata_prefix="igsn",
        setspec=set_spec,
        tfrom=dfrom_date,
        tuntil=dto_date
    )
    session.close()

@click.option("-i", "--service-id", help="ID of service for new job", default=1)
@main.command()
@click.pass_context
def list_jobs(ctx, service_id):
    L = getLogger()
    session = getSession(ctx.obj["engine"])
    service = (
        session.query(igsn_lib.models.Service)
        .filter(igsn_lib.models.Service.id == service_id)
        .one()
    )
    for job in service.jobs:
        print(job)
    session.close()


def igsn_callback(record, igsn):
    print(f"Adding: {igsn.id}")


@click.argument("job-id", default=0)
@main.command()
@click.pass_context
def run_job(ctx, job_id):
    L = getLogger()
    session = getSession(ctx.obj["engine"])
    job = (
        session.query(igsn_lib.models.Job)
        .filter(igsn_lib.models.Job.id == job_id)
        .one()
    )
    job.execute(session, callback=igsn_callback)
    session.close()


