# Python import
import __main__
import os
import webbrowser
from time import time
from functools import partial
# PySide import
from PySide.QtCore import Qt
from PySide.QtGui import QMessageBox, QMenu, QActionGroup, QAction
# Maya import
from maya import cmds
# Custom import
from __init__ import __version__, __author__
import mttOverridePanels
from mttQuickFilterManager import MTTQuickFilterManager
from mttCmd import mtt_log
from mttConfig import (
    MTTSettings, WINDOW_TITLE, TAG, THEMES, PROMPT_INSTANCE_WAIT_DURATION,
    PROMPT_INSTANCE_ASK, PROMPT_INSTANCE_WAIT, PROMPT_INSTANCE_SESSION,
    PROMPT_INSTANCE_STATE)


class MTTSettingsMenu(QMenu):

    def __init__(self, parent=None):
        super(MTTSettingsMenu, self).__init__(parent)

        self.view = parent
        self.is_master_cmd = False
        # power user state
        self.power_user = MTTSettings.value('powerUser')

        self.__create_actions()
        self.__populate_menu()

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            self.is_master_cmd = True

        super(MTTSettingsMenu, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.is_master_cmd = False
        super(MTTSettingsMenu, self).keyReleaseEvent(event)

    def __create_actions(self):
        def add_action(lbl, tip, cmd, checkable=False, checked=False):
            a = QAction(lbl, self)
            a.setStatusTip(tip)
            a.triggered.connect(cmd)
            if checkable:
                a.setCheckable(True)
                a.setChecked(checked)

            return a

        self.help_a = add_action(
            'Help',
            'Opens the online Help page',
            self.on_settings_help)

        self.switch_edit_a = add_action(
            'Switch Edit/Source',
            'Replace "Edit" button by "Source" button',
            self.on_switch_source_edit_menu,
            True,
            MTTSettings.value('switchEdit'))

        self.heads_up_a = add_action(
            'HeadsUp Message',
            'Show HeadsUp Message in viewport',
            self.on_toggle_headsup,
            True,
            MTTSettings.value('showHeadsUp'))

        self.focus_filter_a = add_action(
            'Focus Filter Field at Startup',
            'Focus filter field at startup',
            self.on_toggle_focus,
            True,
            MTTSettings.value('filterFocus'))

        self.force_relative_path_a = add_action(
            'Force Relative Path',
            'Set a relative path when selecting a new file',
            self.on_force_relative_path,
            True,
            MTTSettings.value('forceRelativePath'))

        self.show_real_attr_value_a = add_action(
            'Show Real Attribute Value',
            'Show fullpath instead of filtering path as Attribute Editor',
            self.on_show_real_attribute_value,
            True,
            MTTSettings.value('showRealAttributeValue'))

        self.manage_quick_filter_a = add_action(
            'Manage Quick Filters',
            'Manage filters that popup with right clic in filter field',
            self.on_filter_manage_quick_filter)

        self.clear_completion_cache_a = add_action(
            'Clear Completion Cache',
            'Erase auto completion cache of filter field',
            self.on_filter_clear_completion_cache)

        self.override_panels_a = add_action(
            'Add CreateNode Button to Editors',
            ('Add "Create Node" to HyperShade and '
                'Node Editor for the current session'),
            self.on_override_panels)

        self.export_to_csv = add_action(
            'Export Texture List as CSV',
            'Export current textures into a csv file',
            self.view.model.export_as_csv)

        self.about = add_action(
            'About',
            'About',
            self.on_settings_about)

    def __populate_menu(self):
        self.addAction(self.help_a)

        self.addSeparator()

        self.addAction(self._get_menu_header('SETTINGS'))
        self.addAction(self.switch_edit_a)
        self.addAction(self.heads_up_a)
        self.addAction(self.focus_filter_a)
        self.addAction(self.force_relative_path_a)
        self.addAction(self.show_real_attr_value_a)
        self.addMenu(self._create_instance_menu())
        self.addMenu(self._create_theme_menu())

        self.addSeparator()

        self.addAction(self._get_menu_header('FILTER OPTIONS'))
        self.addAction(self.manage_quick_filter_a)
        self.addAction(self.clear_completion_cache_a)

        self.addSeparator()

        self.addAction(self._get_menu_header('MISC'))
        self.addAction(self.override_panels_a)
        self.addAction(self.export_to_csv)

        self.addSeparator()

        self.addAction(self._get_menu_header('DEBUG'))
        self.addMenu(self._create_debug_menu())

        self.addSeparator()

        self.addAction(self.about)

    def _get_menu_header(self, title):
        header = QAction(title, self)
        header.setEnabled(False)
        return header

    def _create_instance_menu(self):
        self.instance_menu = QMenu(self)
        self.instance_menu.setTitle('Prompt Instance Delay')
        self.instance_menu.aboutToShow.connect(
            self.on_show_prompt_instance_delay_menu)

        return self.instance_menu

    def _create_theme_menu(self):
        theme_menu = QMenu(self)
        theme_menu.setTitle('Buttons Theme')
        theme_menu.setTearOffEnabled(True)
        theme_menu.setWindowTitle(TAG)
        theme_actions = QActionGroup(self)
        theme_actions.setExclusive(True)
        # create ordered theme list
        custom_order_theme = sorted(THEMES.iterkeys())
        custom_order_theme.remove('Maya Theme')
        custom_order_theme.insert(0, 'Maya Theme')
        default_item = True
        for theme in custom_order_theme:
            current_theme_action = QAction(theme, theme_actions)
            current_theme_action.setCheckable(True)
            current_theme_action.setChecked(
                MTTSettings.value('theme', 'Maya Theme') == theme)
            current_theme_action.triggered.connect(self.on_change_theme)
            theme_menu.addAction(current_theme_action)

            if default_item:
                theme_menu.addSeparator()
                default_item = False

        return theme_menu

    def _create_debug_menu(self):
        self.debug_menu = QMenu(self)
        self.debug_menu.setTitle('Debug Menu')
        self.debug_menu.aboutToShow.connect(self.on_show_debug_menu)

        return self.debug_menu

    def on_change_theme(self):
        self.view.on_choose_theme(self.sender().text())

    def on_show_debug_menu(self):
        self.debug_menu.clear()

        if self.is_master_cmd or self.power_user:
            power_user_mode = QAction('Power User Mode', self)
            power_user_mode.setCheckable(True)
            power_user_mode.setChecked(MTTSettings.value('powerUser'))
            power_user_mode.triggered.connect(self.__on_toggle_power_user)
            self.debug_menu.addAction(power_user_mode)
            self.is_master_cmd = False

            self.debug_menu.addSeparator()

        open_pref_folder_action = QAction('Open Preferences Folder', self)
        open_pref_folder_action.setStatusTip('Open MTT preference folder')
        open_pref_folder_action.triggered.connect(self.on_open_preference_folder)
        self.debug_menu.addAction(open_pref_folder_action)

        self.debug_menu.addSeparator()

        database_dump_csv = QAction('Dump Database as CSV', self)
        database_dump_csv.triggered.connect(self.view.model.database_dump_csv)
        self.debug_menu.addAction(database_dump_csv)

        database_dump_sql = QAction('Dump Database as SQL', self)
        database_dump_sql.triggered.connect(self.view.model.database_dump_sql)
        self.debug_menu.addAction(database_dump_sql)

        self.debug_menu.addSeparator()

        support_info = QMenu(self)
        support_info.setTitle('Supported Node Type')
        support_info.aboutToShow.connect(self.on_show_supported_type)
        self.debug_menu.addMenu(support_info)

    def on_filter_clear_completion_cache(self):
        """ Clear filter auto completion cache """
        self.view.on_filter_set_text('')
        MTTSettings.remove('filterCompletionWildcard')
        MTTSettings.remove('filterCompletionRegExp')
        self.view.completion_model.setStringList([])

    def on_switch_source_edit_menu(self):
        state = MTTSettings.value('switchEdit')
        MTTSettings.set_value('switchEdit', not state)
        self.view.on_set_source_edit_menu(not state)

    def on_show_real_attribute_value(self):
        self.view.model.layoutAboutToBeChanged.emit()
        show_real_attribute_state = MTTSettings.value('showRealAttributeValue')
        MTTSettings.set_value(
            'showRealAttributeValue', not show_real_attribute_state)
        self.view._layout_changed()

    def on_filter_manage_quick_filter(self):
        """ Open Quick Filter words manager and save its content """
        manager = MTTQuickFilterManager(self)
        if manager.exec_():
            lists = manager.get_lists()
            # save list in settings
            MTTSettings.set_value('filterQuickWordsWildcard', ';;'.join(lists[0]))
            MTTSettings.set_value('filterQuickWordsRegExp', ';;'.join(lists[1]))
            # set current list
            self.view.quick_filter_words = lists[MTTSettings.value('filterRE')]
        manager.deleteLater()

    @staticmethod
    def on_toggle_headsup():
        state = MTTSettings.value('showHeadsUp')
        MTTSettings.set_value('showHeadsUp', not state)

    @staticmethod
    def on_toggle_focus():
        state = MTTSettings.value('filterFocus')
        MTTSettings.set_value('filterFocus', not state)

    @staticmethod
    def on_force_relative_path():
        state = MTTSettings.value('forceRelativePath')
        MTTSettings.set_value('forceRelativePath', not state)

    def on_show_supported_type(self):
        node_types = sorted(
            [n_type for (n_type, nice, attr) in
             MTTSettings.SUPPORTED_TYPE] + MTTSettings.UNSUPPORTED_TYPE)
        support_info = self.sender()
        support_info.clear()

        for node_type in node_types:
            current = QAction(node_type, self)
            current.setEnabled(False)
            current.setCheckable(True)
            current.setChecked(node_type not in MTTSettings.UNSUPPORTED_TYPE)
            support_info.addAction(current)

    def __on_toggle_power_user(self):
        state = MTTSettings.value('powerUser')
        MTTSettings.set_value('powerUser', not state)
        self.power_user = not state

    @staticmethod
    def on_open_preference_folder():
        """ Open preference folder """
        folder_path = os.path.dirname(MTTSettings.filename())
        cmds.launchImageEditor(viewImageFile=folder_path)

    @staticmethod
    def on_override_panels():
        """ Override HyperShade and NodeEditor creation callback"""
        override_info_box = QMessageBox()
        override_info_box.setWindowTitle(WINDOW_TITLE)
        override_info_box.setIcon(QMessageBox.Information)
        override_info_box.setText(
            'Buttons will be added to HyperShade toolbar and Node Editor toolbar.<br/>'
            'Changes will exists during this session.'
        )
        override_info_box.setInformativeText('<i>Read Help to set this settings permanent</i>')
        override_info_box.setStandardButtons(QMessageBox.Ok)
        override_info_box.setDefaultButton(QMessageBox.Ok)
        override_info_box.exec_()

        mttOverridePanels.override_panels()

    def on_settings_about(self):

        special_list = map(lambda x: x.replace(' ', '&nbsp;'), sorted([
            u'Beno\xeet Stordeur', u'Fran\xe7ois Jumel',
            'Jonathan Lorber', 'Norbert Cretinon',
            'Gilles Hoff'
        ]))
        QMessageBox.about(
            self.parent(),
            WINDOW_TITLE,
            '<b>Maya Texture Toolkit v{:.02f}</b>'
            u'<p>{} - \xa9 2014 - 2016'
            '</p>'
            '<p>Special thanks to :<br/>'
            '<i>{}</i>'
            '</p>'.format(__version__, __author__, ', '.join(special_list))
        )

    @staticmethod
    def on_settings_help():
        help_wiki = 'https://github.com/Bioeden/dbMayaTextureToolkit/wiki'
        webbrowser.open(help_wiki)

    def on_show_prompt_instance_delay_menu(self):
        prompt_instance_state = cmds.optionVar(query='MTT_prompt_instance_state')

        if prompt_instance_state == PROMPT_INSTANCE_WAIT:
            elapsed_time = time() - cmds.optionVar(query='MTT_prompt_instance_suspend')
            if elapsed_time > PROMPT_INSTANCE_WAIT_DURATION:
                prompt_instance_state = PROMPT_INSTANCE_ASK
                cmds.optionVar(iv=['MTT_prompt_instance_state', prompt_instance_state])
            else:
                mtt_log('Remaining %.2fs' % (PROMPT_INSTANCE_WAIT_DURATION - elapsed_time))
        elif prompt_instance_state == PROMPT_INSTANCE_SESSION:
            if 'mtt_prompt_session' not in __main__.__dict__:
                prompt_instance_state = PROMPT_INSTANCE_ASK
                cmds.optionVar(iv=['MTT_prompt_instance_state', prompt_instance_state])

        self.instance_menu.clear()

        prompt_delay = QActionGroup(self)
        prompt_delay.setExclusive(True)
        for i in range(len(PROMPT_INSTANCE_STATE.keys())):
            current_delay_action = QAction(PROMPT_INSTANCE_STATE[i], prompt_delay)
            current_delay_action.setCheckable(True)
            current_delay_action.setChecked(prompt_instance_state == i)
            current_delay_action.triggered.connect(
                partial(self.view.on_choose_instance_delay, i, prompt=i != 0))
            self.instance_menu.addAction(current_delay_action)
