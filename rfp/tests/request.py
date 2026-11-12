"""Helpers for slice 46's tests: a request, documents to attach and the files read back. Synthetic data only
(plan.md §12.1): every file is made by code."""

import email
import io
import zipfile
from email import policy

from django.core.files.uploadedfile import SimpleUploadedFile

import synthetic_files
from documents import services as documents
from rfp import services
from rfp.context import Request
from rfp.xlsx import package

PDF = synthetic_files.text_pdf(['Synthetic attachment'], ['Nothing on this page names a person.'])


def attach(user, deal, kind, name='attachment (synthetic).pdf', **meta):
    """A document filed on the deal through documents' own door."""
    return documents.upload(user, deal, SimpleUploadedFile(name, PDF), {'kind': kind, **meta}, log=False)


def ask(user, deal, *carriers, **settings):
    """Pick carriers (and any other setting) through rfp's own service."""
    changes = {**settings}
    if carriers:
        changes['carriers'] = {'add': list(carriers)}
    return services.update(user, deal.id, changes)


def ctx(deal):
    deal.refresh_from_db()
    return Request(deal)


def get(api, deal, key, **params):
    return api.get(f'/api/deals/{deal.id}/rfp/files/{key}/', params)


def body(response):
    return b''.join(response.streaming_content) if response.streaming else response.content


def cell(content, sheet, ref):
    found, shared = package.read_sheet(content, sheet)
    return found.text_at(ref, shared)


def unzip(content):
    archive = zipfile.ZipFile(io.BytesIO(content))
    return {name: archive.read(name) for name in archive.namelist()}


def message(content):
    return email.message_from_bytes(content, policy=policy.default)
