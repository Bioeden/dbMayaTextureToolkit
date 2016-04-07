# Python import
import os
import shutil
from functools import partial

# Maya import
import maya.cmds as cmds
import maya.mel as mel

# Custom import
from mttFilterFileDialog import create_nodes


MTT_ICONS_NAME = ['MTT_CreateNode.png']
ICON_SIZE = 26

VAR_HS_CMD = 'MTT_hs_panel_custom_cmd'
VAR_NE_CMD = 'MTT_ne_panel_custom_cmd'


def hypershade_add_node(panel):
    mel.eval('hyperShadePanelGraphCommand("%s", "addSelected")' % panel)


def hypershade_remove_node(panel):
    mel.eval('hyperShadePanelGraphCommand("%s", "removeSelected")' % panel)


def override_add_hypershade_panel(panel):
    # create HyperShade with Maya command
    if cmds.optionVar(exists=VAR_HS_CMD):
        mel.eval('%s("%s")' % (cmds.optionVar(query=VAR_HS_CMD), panel))
    else:
        mel.eval('addHyperShadePanel("%s")' % panel)

    # set HyperShade toolbar current parent (name is hardcoded in mel files)
    cmds.setParent('hyperShadeToolbarForm')

    # add custom buttons
    cmds.separator(height=ICON_SIZE, horizontal=False, style='single')

    cmds.iconTextButton(
        image='nodeGrapherAddNodes.png',
        width=ICON_SIZE,
        height=ICON_SIZE,
        command=partial(hypershade_add_node, panel)
    )

    cmds.iconTextButton(
        image='nodeGrapherRemoveNodes.png',
        width=ICON_SIZE,
        height=ICON_SIZE,
        command=partial(hypershade_remove_node, panel)
    )

    cmds.separator(height=ICON_SIZE, horizontal=False, style='single')

    cmds.iconTextButton(
        image='MTT_CreateNode.png',
        width=ICON_SIZE,
        height=ICON_SIZE,
        command=create_nodes
    )


def override_add_node_editor_panel(panel):
    # create Node Editor with Maya command
    if cmds.optionVar(exists=VAR_NE_CMD):
        mel.eval('%s("%s")' % (cmds.optionVar(query=VAR_NE_CMD), panel))
    else:
        mel.eval('nodeEdAddCallback("%s")' % panel)

    # set Node Editor toolbar current parent
    form_layout = cmds.layout(panel, query=True, childArray=True)[0]
    frame_layout = cmds.layout(form_layout, query=True, childArray=True)[0]
    flow_layout = cmds.layout(frame_layout, query=True, childArray=True)[0]
    cmds.setParent(flow_layout)

    # add custom buttons
    cmds.separator(height=ICON_SIZE, horizontal=False, style='single')

    cmds.iconTextButton(
        image='MTT_CreateNode.png',
        width=ICON_SIZE,
        height=ICON_SIZE,
        command=create_nodes
    )


def override_panels(custom_hs_cmd=None, custom_ne_cmd=None):
    # check if icons is in maya resources, if not, copy into userBitmapsDir
    user_icons_path = cmds.internalVar(userBitmapsDir=True)
    mtt_icons_path = os.path.join(os.path.dirname(__file__), 'icons')
    maya_icons = os.listdir(user_icons_path)

    for ico in MTT_ICONS_NAME:
        if ico not in maya_icons:
            source_file = os.path.join(mtt_icons_path, ico)
            destination_file = os.path.join(user_icons_path, ico)
            shutil.copy2(source_file, destination_file)

    # create MEL global proc
    cmd = mel.createMelWrapper(
        override_add_hypershade_panel, types=['string'], returnCmd=True)
    mel.eval(cmd)
    cmd = mel.createMelWrapper(
        override_add_node_editor_panel, types=['string'], returnCmd=True)
    mel.eval(cmd)

    # edit callback of scripted panel
    cmds.scriptedPanelType(
        'hyperShadePanel', edit=True,
        addCallback='override_add_hypershade_panel')

    cmds.scriptedPanelType(
        'nodeEditorPanel', edit=True,
        addCallback='override_add_node_editor_panel')

    # store custom cmd
    if custom_hs_cmd:
        cmds.optionVar(sv=[VAR_HS_CMD, custom_hs_cmd])
    if custom_ne_cmd:
        cmds.optionVar(sv=[VAR_NE_CMD, custom_hs_cmd])
