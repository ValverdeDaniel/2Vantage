"""GET /api/meta/ — every vocabulary the frontend needs (plan.md §7.1). The frontend never hard-codes these."""

from rest_framework.response import Response
from rest_framework.views import APIView

from agenda import meta as agenda_meta
from ai import client as ai_client
from ai import selectors as ai_selectors
from census import fields as census_fields
from commission import vocab as commission_vocab
from deals import carriers, comp, contacts, lifecycle, lines, rules, stages
from deals.models import Note
from documents import kinds, review_rules
from intake import coverage as intake_coverage
from intake import form as intake_form
from proposals import catalog as proposal_catalog
from questionnaire import forms as questionnaire_forms
from quotes import board_presets, fields, stop_loss_board
from quotes.math import enrollment as quote_enrollment
from review import meta as review_meta
from rfp import meta as rfp_meta


def _pairs(choices):
    return [{'key': key, 'label': label} for key, label in choices]


class MetaView(APIView):
    def get(self, request):
        return Response(
            {
                'lines': lines.meta(),
                'tiers': [{'code': code, 'label': label} for code, label in lines.TIERS],
                'stages': _pairs(stages.STAGES),
                'relationships': lifecycle.meta(),
                'funding': _pairs(lines.FUNDING),
                **kinds.meta(),  # document_kinds (with their flags), document_buckets, document_roles
                **review_rules.meta(),  # review_buckets: the station List's eight buckets, worst first (E56)
                'plans': fields.meta(),
                'carriers': carriers.meta(),
                'board': board_presets.meta(),  # the Advisor's columns, sorts, sliders and budget rungs (F31)
                'enrollment': quote_enrollment.meta(),  # enrollment sources in words, keys by basis (F86, F92)
                'stop_loss': stop_loss_board.meta(),  # the stop-loss board's rank keys, terms, settings (F102)
                'commission_types': comp.meta(),  # pct, flat, pepm (§4.6)
                'commission': commission_vocab.meta(),  # roles, kinds, bases, sources, scopes (H10–H24; slice 48)
                'contact_roles': contacts.meta(),  # the seven roles, client side or not (§4.6, OQ106; slice 38)
                'note_kinds': _pairs(Note.KINDS),  # note, call, email, meeting, internal (A37; slice 38)
                'deal_types': _pairs(rules.DEAL_TYPES),  # New business, Renewal (M14)
                # the intake questions (§4.5) and the coverage card's words (B16–B21)
                'intake': {'form': intake_form.meta(), 'coverage': intake_coverage.meta()},
                'census': census_fields.meta(),  # the 45 columns, groups, choices, rules (§4.4)
                'questionnaires': questionnaire_forms.meta(),  # the forms, their items and choices (G1, G3; slice 42)
                'rfp': rfp_meta.meta(),  # the RFP tab's cards, bands, routes, funding and carriers (K.6; slice 44)
                'proposal': proposal_catalog.meta(),  # the builder's cards, parts, layouts and limits (J.6.6; slice 25)
                'review': review_meta.meta(),  # link levels, request and link states, close reasons (L.6; slice 53)
                'agenda': agenda_meta.meta(),  # sections, step titles, follow-up days, Later picks (I.6; slice 60)
                **({'ai': ai_selectors.meta()} if ai_client.available() else {}),  # only with a key (D26; slice 18)
            }
        )
