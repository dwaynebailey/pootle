# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import pytest

from pootle_app.project_tree import direct_language_match_filename
from pytest_pootle.factories import LanguageDBFactory


@pytest.mark.parametrize('language_code, path_name, matched', [
    # language codes as filenames
    ('pt_BR', '/path/to/pt_BR.po', True),
    ('pt_BR', '/path/to/pt_br.po', True),
    ('pt-BR', '/path/to/pt-BR.po', True),
    ('pt-BR', '/path/to/pt-br.po', True),
    ('pt-br', '/path/to/pt-BR.po', True),
    ('pt-br', '/path/to/pt-br.po', True),
    ('pt_br', '/path/to/pt_BR.po', True),
    ('pt_br', '/path/to/pt_br.po', True),

    # xx_YY != xx-YY
    pytest.mark.xfail(('pt_BR', '/path/to/pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/pt-br.po', True)),
    pytest.mark.xfail(('pt-BR', '/path/to/pt_BR.po', True)),
    pytest.mark.xfail(('pt-BR', '/path/to/pt_br.po', True)),

    ('br', '/path/to/br.po', True),
    ('br', '/path/to/BR.po', True),

    ('kmr-Latn', '/path/to/kmr-Latn.po', True),
    ('ca-valencia', '/path/to/ca-valencia.po', True),
    ('ca@valencia', '/path/to/ca@valencia.po', True),


    #
    # prefix == file
    #

    ('pt_BR', '/path/to/file-pt_BR.po', True),
    ('pt_BR', '/path/to/file_pt_BR.po', True),
    ('pt_BR', '/path/to/file.pt_BR.po', True),
    ('pt_BR', '/path/to/file-pt_br.po', True),
    ('pt_BR', '/path/to/file_pt_br.po', True),
    ('pt_BR', '/path/to/file.pt_br.po', True),

    # xx_YY != xx-YY
    pytest.mark.xfail(('pt_BR', '/path/to/file-pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/file_pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/file.pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/file-pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/file_pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/file.pt-br.po', True)),

    # any separator works for the most common case
    ('br', '/path/to/file-br.po', True),
    ('br', '/path/to/file_br.po', True),
    ('br', '/path/to/file.br.po', True),
    ('br', '/path/to/file-BR.po', True),
    ('br', '/path/to/file_BR.po', True),
    ('br', '/path/to/file.BR.po', True),

    # no multiple matching
    ('br', '/path/to/file-pt_BR.po', False),
    ('br', '/path/to/file_pt_BR.po', False),
    ('br', '/path/to/file.pt_BR.po', False),
    ('br', '/path/to/file-pt-BR.po', False),
    ('br', '/path/to/file_pt-BR.po', False),
    ('br', '/path/to/file.pt-BR.po', False),

    ('br', '/path/to/file-pt_br.po', False),
    ('br', '/path/to/file_pt_br.po', False),
    ('br', '/path/to/file.pt_br.po', False),
    ('br', '/path/to/file-pt-br.po', False),
    ('br', '/path/to/file_pt-br.po', False),
    ('br', '/path/to/file.pt-br.po', False),

    pytest.mark.xfail(('kmr-Latn', '/path/to/file-kmr-Latn.po', True)),
    pytest.mark.xfail(('ca-valencia', '/path/to/file-ca-valencia.po', True)),
    ('ca@valencia', '/path/to/file-ca@valencia.po', True),
    pytest.mark.xfail(('ca-valencia', '/path/help-ui-ca-valencia.po', True)),
    pytest.mark.xfail(('ca@valencia', '/path/help-ui-ca@valencia.po', True)),

    pytest.mark.xfail(('kmr-Latn', '/path/to/file.kmr-Latn.po', True)),
    pytest.mark.xfail(('ca-valencia', '/path/to/file.ca-valencia.po', True)),
    ('ca@valencia', '/path/to/file.ca@valencia.po', True),
    pytest.mark.xfail(('ca-valencia', '/path/help-ui.ca-valencia.po', True)),
    ('ca@valencia', '/path/help-ui.ca@valencia.po', True),

    #
    # template name is "pt.pot" (prefix == "pt")
    #

    # multiple matching possible
    pytest.mark.xfail(('br', '/path/to/pt_br.po', True)),
    pytest.mark.xfail(('br', '/path/to/pt_BR.po', True)),
    pytest.mark.xfail(('br', '/path/to/pt-br.po', True)),
    pytest.mark.xfail(('br', '/path/to/pt-BR.po', True)),

    # "." works as separator
    ('br', '/path/to/pt.br.po', True),
    ('br', '/path/to/pt.BR.po', True),
    ('pt_BR', '/path/to/pt.br.po', False),
    ('pt_BR', '/path/to/pt.BR.po', False),


    #
    # template name ends with "-ui" or "_ui" or ".ui"
    #

    pytest.mark.xfail(('br', '/path/to/help-ui-br.po', True)),
    pytest.mark.xfail(('br', '/path/to/help-ui_br.po', True)),
    ('br', '/path/to/help-ui.br.po', True),

    pytest.mark.xfail(('br', '/path/to/help_ui-br.po', True)),
    pytest.mark.xfail(('br', '/path/to/help_ui_br.po', True)),
    ('br', '/path/to/help_ui.br.po', True),

    pytest.mark.xfail(('br', '/path/to/help.ui-br.po', True)),
    pytest.mark.xfail(('br', '/path/to/help.ui_br.po', True)),
    ('br', '/path/to/help.ui.br.po', True),

    ('br', '/path/to/help-uiui-br.po', True),
    ('br', '/path/to/help_uiui-br.po', True),
    ('br', '/path/to/help.uiui-br.po', True),
    ('br', '/path/to/help-uiui_br.po', True),
    ('br', '/path/to/help_uiui_br.po', True),
    ('br', '/path/to/help.uiui_br.po', True),
    ('br', '/path/to/help-uiui.br.po', True),
    ('br', '/path/to/help_uiui.br.po', True),
    ('br', '/path/to/help.uiui.br.po', True),

    #
    # "-" separator
    #

    ('pt_BR', '/path/to/help-ui-pt_BR.po', True),
    ('pt_BR', '/path/to/help_ui-pt_BR.po', True),
    ('pt_BR', '/path/to/help.ui-pt_BR.po', True),

    # xx_YY != xx-YY
    pytest.mark.xfail(('pt_BR', '/path/to/help-ui-pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help_ui-pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help.ui-pt-BR.po', True)),

    ('pt_BR', '/path/to/help-ui-pt_br.po', True),
    ('pt_BR', '/path/to/help_ui-pt_br.po', True),
    ('pt_BR', '/path/to/help.ui-pt_br.po', True),

    # xx_YY != xx-YY
    pytest.mark.xfail(('pt_BR', '/path/to/help-ui-pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help_ui-pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help.ui-pt-br.po', True)),

    #
    #  "_" separator
    #

    ('pt_BR', '/path/to/help-ui_pt_BR.po', True),
    ('pt_BR', '/path/to/help_ui_pt_BR.po', True),
    ('pt_BR', '/path/to/help.ui_pt_BR.po', True),

    # xx_YY != xx-YY
    pytest.mark.xfail(('pt_BR', '/path/to/help-ui_pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help_ui_pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help.ui_pt-BR.po', True)),

    ('pt_BR', '/path/to/help-ui_pt_br.po', True),
    ('pt_BR', '/path/to/help_ui_pt_br.po', True),
    ('pt_BR', '/path/to/help.ui_pt_br.po', True),

    pytest.mark.xfail(('pt_BR', '/path/to/help-ui_pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help_ui_pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help.ui_pt-br.po', True)),

    #
    #  "." separator
    #
    ('pt_BR', '/path/to/help-ui.pt_BR.po', True),
    ('pt_BR', '/path/to/help_ui.pt_BR.po', True),
    ('pt_BR', '/path/to/help.ui.pt_BR.po', True),

    # xx_YY != xx-YY
    pytest.mark.xfail(('pt_BR', '/path/to/help-ui.pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help_ui.pt-BR.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help.ui.pt-BR.po', True)),

    ('pt_BR', '/path/to/help-ui.pt_br.po', True),
    ('pt_BR', '/path/to/help_ui.pt_br.po', True),
    ('pt_BR', '/path/to/help.ui.pt_br.po', True),

    # xx_YY != xx-YY
    pytest.mark.xfail(('pt_BR', '/path/to/help-ui.pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help_ui.pt-br.po', True)),
    pytest.mark.xfail(('pt_BR', '/path/to/help.ui.pt-br.po', True)),



])
@pytest.mark.django_db
def test_direct_language_match_filename(language_code, path_name, matched):
    LanguageDBFactory(code="pt_BR")
    assert direct_language_match_filename(language_code, path_name) is matched
