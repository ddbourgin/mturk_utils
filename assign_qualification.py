#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter

import boto3

DESCRIPTION = \
    """
Assign a qualification to a given worker ID/IDs. Useful for setting up
invitation-only makeup HITs.

Usage
-----
    >>> export AWS_ACCESS_KEY_ID=<MTurk access key id>
    >>> export AWS_SECRET_ACCESS_KEY=<MTurk secret access key>
    >>> assign_qualification.py <qualification id> <worker id>
"""


class CustomFormatter(ArgumentDefaultsHelpFormatter, RawDescriptionHelpFormatter):
    pass


def all_pages(func, **kwargs):
    """Handle pagination for boto3 AWS requests"""
    response = func(**kwargs)
    pages = [response]
    while response['NumResults'] > 0:
        response = func(
            NextToken=response['NextToken'],
            **kwargs
        )
        pages += [response]
    return pages


def mturk_client():
    print("Connecting to mechanical turk...")
    key_id = os.environ['AWS_ACCESS_KEY_ID']
    key = os.environ['AWS_SECRET_ACCESS_KEY']

    client = boto3.client(
        'mturk',
        aws_access_key_id=key_id,
        aws_secret_access_key=key
    )
    return client


if __name__ == "__main__":
    parser = ArgumentParser(
        description=DESCRIPTION,
        formatter_class=CustomFormatter)

    parser.add_argument(
        "qualification",
        metavar="QUALIFICATION",
        help="qualification ID")

    parser.add_argument(
        "--value",
        default=1,
        type=int,
        help="qualification value")

    parser.add_argument(
        "workers",
        metavar="WORKER",
        nargs="*",
        help="worker ID")

    args = parser.parse_args()

    client = mturk_client()

    # get workers who already have the qualification
    pages = all_pages(
        client.list_workers_with_qualification_type,
        QualificationTypeId=args.qualification,
        Status='Granted',
        MaxResults=100
    )

    workers_w_qualification = set()
    for page in pages:
        for worker in page['Qualifications']:
            workers_w_qualification.add(worker['WorkerId'])

    for worker in args.workers:
        # if the worker doesn't already have the qualification, assign it,
        # otherwise just update the qualification score
        if worker not in workers_w_qualification:
            print("Assigning qualification '{}' to worker '{}'"
                  .format(args.qualification, worker))
        else:
            print("Updating qualification '{}' for worker '{}'"
                  .format(args.qualification, worker))

        result = client.associate_qualification_with_worker(
            QualificationTypeId=args.qualification,
            WorkerId=worker,
            IntegerValue=args.value,
            SendNotification=True
        )

    print('\nFinished assigning qualifications')

    # print out the final set of workers with the qualification
    pages = all_pages(
        client.list_workers_with_qualification_type,
        QualificationTypeId=args.qualification,
        Status='Granted',
        MaxResults=100
    )

    workers_w_qualification = []
    for page in pages:
        for worker in page['Qualifications']:
            workers_w_qualification.append(worker)

    print("{} workers with qualification {}:"
          .format(len(workers_w_qualification), args.qualification))

    for ix, worker in enumerate(workers_w_qualification):
        print("\t{}. {} (value: {})".format(
            ix + 1, worker['WorkerId'], worker['IntegerValue']))
