# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

# django.conf.urls.url() (and this whole codebase's urls.py files
# import it the same way) is deprecated as of Django 3.1, removed in
# 4.0; django.urls.re_path() is its exact successor (url() always
# only ever accepted regex patterns, same as re_path()). Aliasing the
# import rather than renaming every url(...) call site across ~16
# files. Phase 2 rung 2 (Django 2.2 -> 3.2); see PORTING.md.
from django.conf import settings
from django.urls import include, re_path as url
from django.views.generic import TemplateView

from pootle.core.delegate import url_patterns


urlpatterns = []

# Allow url handlers to be overriden by plugins
for delegate_urls in url_patterns.gather().values():
    urlpatterns += delegate_urls

urlpatterns += [
    # Allauth
    url(r'^accounts/', include('accounts.urls')),
    url(r'^accounts/', include('allauth.urls')),
]

# XXX should be autodiscovered
if "import_export" in settings.INSTALLED_APPS:
    urlpatterns += [
        # Pootle offline translation support URLs.
        url(r'', include('import_export.urls')),
    ]

urlpatterns += [
    # External apps
    url(r'^contact/', include('contact.urls')),
    url(r'', include('pootle_profile.urls')),

    # Pootle URLs
    url(r'', include('staticpages.urls')),
    url(r'^help/quality-checks/',
        TemplateView.as_view(template_name="help/quality_checks.html"),
        name='pootle-checks-descriptions'),
    url(r'', include('pootle_app.urls')),
    url(r'^projects/', include('pootle_project.urls')),
    url(r'', include('pootle_terminology.urls')),
    url(r'', include('pootle_statistics.urls')),
    url(r'', include('pootle_store.urls')),
    url(r'', include('pootle_language.urls')),
    url(r'', include('pootle_translationproject.urls')),
]


# TODO: handler400
handler403 = 'pootle.core.views.permission_denied'
handler404 = 'pootle.core.views.page_not_found'
handler500 = 'pootle.core.views.server_error'
