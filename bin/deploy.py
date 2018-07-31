#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#   Copyright 2018 Nick Boultbee
#   This file is part of squeeze-alexa.
#
#   squeeze-alexa is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   See LICENSE for full license

import argparse
import json
import logging
import re
import sys
from io import BytesIO
from os import path, walk, chdir
from os.path import dirname
from typing import BinaryIO
from zipfile import ZipFile, ZIP_DEFLATED

import boto3

from botocore.exceptions import ClientError

LAMBDA_NAME = "squeeze-alexa"
MANAGED_POLICY_ARN = ("arn:aws:iam::aws:policy/service-role/"
                      "AWSLambdaBasicExecutionRole")
ROLE_NAME = "squeeze-alexa"
EXCLUDE_REGEXES = [re.compile(s) for s in
                   ("__pycache__/", "\.git/", "\.dist-info/",
                    "docs/", "metadata/",
                    "\.po$", r"~$", "\.pyc$", "\.md$", "\.zip$")]

logging.basicConfig(format="[{levelname:7s}] {message}",
                    style="{")
log = logging.getLogger("squeeze-alexa-uploader")
log.setLevel(logging.DEBUG)

ROLE_POLICY_DOC = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
})

Arn = str


def suitable(name: str) -> bool:
    for r in EXCLUDE_REGEXES:
        if r.search(name):
            return False
    return True


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="squeeze-alexa uploader")
    parser.add_argument("--profile", action="store")
    parser.add_argument("--skill", required=True, action="store",
                        help="Your Alexa skill ID (without 'amzn1.ask.skill')")
    args = parser.parse_args(args)
    if args.profile:
        session = boto3.session.Session()
        log.debug("Available profiles: %s", session.available_profiles)
        log.info("Using profile: %s", args.profile)
        boto3.setup_default_session(profile_name=args.profile)

    dist_dir = path.join(dirname(dirname(__file__)), "dist")
    logging.info("Taking built code from %s", dist_dir)
    chdir(dist_dir)

    zip_data = create_zip()

    role_arn = set_up_role()
    if lambda_exists():
        upload(zip_data)
    else:
        arn = create_lambda(role_arn, zip_data, args.skill)
        print("Lambda ARN:", arn)


def lambda_exists(name=LAMBDA_NAME) -> bool:
    lam = boto3.client("lambda")
    try:
        lam.get_function(FunctionName=name)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        return False
    else:
        log.info("AWS Lambda '%s' already exists. Updating code only...", name)
        return True


def upload(zip: BinaryIO, name=LAMBDA_NAME):
    lam = boto3.client("lambda")
    r = lam.update_function_code(FunctionName=name,
                                 ZipFile=zip.read())
    log.info("Updated Lambda: %s", r['FunctionArn'])
    log.info("Updated %s (\"%s\"), with %.0f KB of zipped data",
             name, r["Description"], r["CodeSize"] / 1024)


def create_lambda(role_arn: str, zip_data: BinaryIO, skill_id: str) -> Arn:
    lam = boto3.client("lambda")
    resp = lam.create_function(FunctionName=LAMBDA_NAME,
                               Runtime="python3.6",
                               Handler="handler.lambda_handler",
                               Code={"ZipFile": zip_data.read()},
                               Description="Squeezebox integration for Alexa",
                               Role=role_arn,
                               Timeout=8)
    log.debug("Creation response: %s", resp)

    r = lam.add_permission(
        FunctionName=LAMBDA_NAME,
        StatementId="AlexaFunctionPermission",
        Action="lambda:InvokeFunction",
        Principal="alexa-appkit.amazon.com",
        EventSourceToken="amzn1.ask.skill.%s" % skill_id)
    log.debug("Permissioning response: %s", r)
    return resp["FunctionArn"]


def create_zip() -> BinaryIO:
    io = BytesIO()
    with ZipFile(io, "w") as zf:
        for root, dirs, fns in walk("./"):
            for d in list(dirs):
                if not suitable(d + "/"):
                    dir_path = path.join(root, d)
                    log.info("Excluding dir: %s", dir_path)
                    try:
                        dirs.remove(d)
                    except ValueError:
                        log.warning("Couldn't remove %s", dir_path)
            for name in fns:
                if suitable(name):
                    zf.write(path.join(root, name), compress_type=ZIP_DEFLATED)
    log.debug("All files: %s", ", ".join(zi.filename for zi in zf.filelist))
    io.seek(0)
    log.info("Size of ZIP: %.0f KB", len(io.read()) / 1024)
    io.seek(0)
    return io


def set_up_role() -> str:
    iam = boto3.client("iam")

    def create_role() -> dict:
        response = iam.create_role(RoleName=ROLE_NAME,
                                   AssumeRolePolicyDocument=ROLE_POLICY_DOC)
        iam.attach_role_policy(RoleName=ROLE_NAME,
                               PolicyArn=MANAGED_POLICY_ARN)
        return response

    try:
        role = create_role()
    except ClientError as e:
        if e.response["Error"]["Code"] != "EntityAlreadyExists":
            raise
        try:
            logging.info("Deleting existing role...")
            iam.delete_role(RoleName=ROLE_NAME)
        except ClientError:
            logging.info("Detaching existing role first...")
            role = boto3.resource("iam").Role(ROLE_NAME)
            role.detach_policy(PolicyArn=MANAGED_POLICY_ARN)
            role.delete()
        role = create_role()
    return role["Role"]["Arn"]


if __name__ == "__main__":
    main()
