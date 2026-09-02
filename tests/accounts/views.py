# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from django.http import QueryDict

from allauth.account.models import EmailAddress


@pytest.mark.django_db
def test_accounts_login(client, request_users, settings):
    user = request_users["user"]
    if user.username == "nobody":
        return

    settings.POOTLE_CAPTCHA_ENABLED = False
    password = request_users["password"]
    qdict = QueryDict(mutable=True)
    qdict.update(
        {'login': user.username,
         'password': password})
    qdict._mutable = False
    response = client.post(
        '/accounts/login/',
        qdict,
        HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    email = EmailAddress.objects.filter(user=user, primary=True).first()
    assert response.request['PATH_INFO'] == '/accounts/login/'
    assert response.status_code == 200
    if email is not None and email.verified:
        assert response.json() == {u"location": "/"}
    else:
        assert response.json() == {u"location": "/accounts/confirm-email/"}


@pytest.mark.django_db
def test_accounts_logout(client, request_users, settings):
    user = request_users["user"]
    if user.username == "nobody":
        return

    settings.POOTLE_CAPTCHA_ENABLED = False
    if user.username != "nobody":
        client.login(
            username=user.username,
            password=request_users["password"])

    response = client.post(
        '/accounts/logout/',
        {},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    # allauth's LogoutView didn't route AJAX POSTs through
    # _ajax_response()/PootleAccountAdapter.ajax_response() (the same
    # override test_accounts_login above already exercises) until
    # somewhere between 0.35.0 and 0.42.0 (see requirements/
    # django22.txt's own note on the version bump) - it used to return
    # a genuine 302 redirect unconditionally. Now logout gets the same
    # ajax-aware JSON response login always got, which is the correct,
    # intentional behavior of our own adapter, not a regression - only
    # this test's expectation was stale. Phase 2 rung 1 (Django 1.11 ->
    # 2.2); see PORTING.md.
    assert response.status_code == 200
    assert response.json() == {u"location": "/"}
