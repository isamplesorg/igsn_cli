"""
Command line client for working with International Geo Sample Numbers (IGSNs).

Supported by NSF Award 2004815
"""
import sys
import logging
import datetime
import json
import click
import dateparser
import igsn_lib.models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy.orm.exc

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
    default="INFO",
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
@click.option(
    "-F",
    "--format",
    default="json",
    help="Ouput format",
    show_default=True
)
@click.pass_context
def main(ctx, verbosity, db_connect, format):
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
    ctx.obj["format"] = format


@main.command()
@click.pass_context
def services(ctx):
    session = getSession(ctx.obj["engine"])
    res = []
    for service in session.query(igsn_lib.models.Service).all():
        if ctx.obj['format'] == 'json':
            res.append(service.asJsonDict())
        else:
            print(service)
    session.close()
    if ctx.obj['format'] == 'json':
        print(json.dumps(res, indent=2))


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
@click.argument("service-id", default=1)
@click.option(
    "-c",
    "--counts",
    help="Get record counts per set",
    default=False,
    show_default=True,
    is_flag=True,
)
def sets(ctx, service_id, counts):
    L = getLogger()
    session = getSession(ctx.obj["engine"])
    try:
        service = (
            session.query(igsn_lib.models.Service)
            .filter(igsn_lib.models.Service.id == service_id)
            .one()
        )
        L.info("Service: %s", service.url)
        sets = service.listSets(get_counts=counts)
        if ctx.obj['format'] == 'json':
            print(json.dumps(sets, indent=2))
        else:
            for s in sets:
                if counts:
                    print(f"{s['setSpec']}: {s['count']}: {s['setName']}")
                else:
                    print(f"{s['setSpec']}: {s['setName']}")
    except sqlalchemy.orm.exc.NoResultFound as e:
        L.error("No service found with ID=%s", service_id)
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
    if dto_date is not None and dfrom_date is not None:
        if dto_date < dfrom_date:
            L.error("from-date must be older than to-date")
            return 1
    session = getSession(ctx.obj["engine"])
    try:
        service = (
            session.query(igsn_lib.models.Service)
            .filter(igsn_lib.models.Service.id == service_id)
            .one()
        )
        job = service.createJob(
            session=session,
            ignore_deleted=False,
            metadata_prefix="igsn",
            setspec=set_spec,
            tfrom=dfrom_date,
            tuntil=dto_date,
        )
        print(job)
    except sqlalchemy.orm.exc.NoResultFound as e:
        L.error("No service found with ID=%s", service_id)
    session.close()


@click.argument("service-id", default=1)
@main.command()
@click.pass_context
def jobs(ctx, service_id):
    L = getLogger()
    session = getSession(ctx.obj["engine"])
    res = []
    try:
        service = (
            session.query(igsn_lib.models.Service)
            .filter(igsn_lib.models.Service.id == service_id)
            .one()
        )
        for job in service.jobs:
            if ctx.obj['format'] == 'json':
                res.append(job.asDict())
            else:
                print(job)
    except sqlalchemy.orm.exc.NoResultFound as e:
        L.error("No service found with ID=%s", service_id)
    session.close()
    if ctx.obj['format'] == 'json':
        print(json.dumps(res, indent=2))


@click.argument("job-id", default=0)
@main.command()
@click.pass_context
def delete_job(ctx, job_id):
    L = getLogger()
    session = getSession(ctx.obj["engine"])
    try:
        job = (
            session.query(igsn_lib.models.Job)
            .filter(igsn_lib.models.Job.id == job_id)
            .one()
        )
        session.delete(job)
        session.commit()
        L.info("Deleted job id=%s", job.id)
    except sqlalchemy.orm.exc.NoResultFound as e:
        L.error("No job found with ID=%s", job_id)
    session.close()


def igsn_callback(record, igsn):
    print(f"Adding: {igsn.id}")


@click.argument("job-id", default=0)
@main.command()
@click.pass_context
def run_job(ctx, job_id):
    L = getLogger()
    session = getSession(ctx.obj["engine"])
    try:
        job = (
            session.query(igsn_lib.models.Job)
            .filter(igsn_lib.models.Job.id == job_id)
            .one()
        )
        job.execute(session, callback=igsn_callback)
    except sqlalchemy.orm.exc.NoResultFound as e:
        L.error("No job found with ID=%s", job_id)
    session.close()

@click.argument("service-id", default=1)
@click.option("-s", "--setspec", default=None, help="Setspec name (compared using LIKE)")
@main.command()
@click.pass_context
def last_record(ctx, service_id, setspec):
    L = getLogger()
    session = getSession(ctx.obj["engine"])
    res = {}
    try:
        service = (
            session.query(igsn_lib.models.Service)
            .filter(igsn_lib.models.Service.id == service_id)
            .one()
        )
        last_record = service.mostRecentIdentifierRetrieved(session, set_spec=setspec)
        res = last_record.asJsonDict()
    except sqlalchemy.orm.exc.NoResultFound as e:
        L.error("No service found with ID=%s", service_id)
    except AttributeError as e:
        L.error("No matching record for service_id=%s and set_spec=%s", service_id, setspec)
    session.close()
    if ctx.obj['format'] == 'json':
        print(json.dumps(res, indent=2))

