""" Maya Texture Toolkit

Maya Texture Toolkit aims to help artist to manage
and work easily with textures in Maya
https://github.com/Bioeden/dbMayaTextureToolkit


Launch command
==============
-- MAIN UI --
import dbMayaTextureToolkit as MTT
reload(MTT)
MTT.show_ui(toggle=True)

-- SHADING NODE CREATION --
import dbMayaTextureToolkit as MTT
MTT.create_nodes(define_path=None, define_type=None)

-- VIEWER --
import dbMayaTextureToolkit as MTT
mViewer = MTT.mttViewer.MTTViewer()
mViewer.show()
mViewer.show_image('path/to/image.ext')

-- ADD HYPERSHADE AND NODE EDITOR BUTTONS PERMANENTLY --
# add this lines to your userSetup.py in your Maya script directory
import maya.cmds as cmds
cmds.evalDeferred(
    "import dbMayaTextureToolkit.mttOverridePanels as orp;orp.override_panels()"
)


JSON file help
==============
TODO JSON guide

http://www.jsoneditoronline.org/

Default JSON content
{
  "supportedNodeType":[
    {
      "node_type":"file",
      "node_nicename":"FILE",
      "node_attr":"fileTextureName"
    },
    {
      "node_type":"psdFileTex",
      "node_nicename":"PSD",
      "node_attr":"fileTextureName"
    },
    {
      "node_type":"mentalrayTexture",
      "node_nicename":"MRT",
      "node_attr":"fileTextureName"
    }
  ],
  "workspaceExtend":{
    "textureSourceFolder":"<WORKSPACE>/PSD/"
  },
  "customButton":[
    {
      "icon":":/activeSelectedAnimLayer.png",
      "tooltip":"User Button Example",
      "cmd":"cmds.TextureViewWindow"
    }
  ],
  "import_policy":"from dbMayaTextureToolkit.mttImportPolicy import exec_import_policy",
  "path_pattern":"E:\\CG_Projects\\Demo_MTT",
  "VCS": {
    "checkout": "from dbMayaTextureToolkit.mttSourceControlTemplate import checkout",
    "submit": "from dbMayaTextureToolkit.mttSourceControlTemplate import submit",
    "revert": "from dbMayaTextureToolkit.mttSourceControlTemplate import revert"
  }
}

"""
# Python import
import sys
# Maya import
from maya import cmds


__author__ = u'David Bole aka Bioeden'
__version__ = 1.10


# reload all package modules if new version is detected
if cmds.optionVar(query='MTT_version') < __version__:
    # update version number
    cmds.optionVar(fv=['MTT_version', __version__])

    # close window to save pref before unload modules
    if cmds.control('dbMayaTextureToolkitWin', exists=True):
        cmds.deleteUI('dbMayaTextureToolkitWin', window=True)

    # break module path
    package_name = '{}.'.format(__package__)
    for mod in sys.modules.keys():
        if mod.startswith(package_name):
            del sys.modules[mod]


# init settings
import mttConfig
mttConfig.MTTSettings()


def show_ui(toggle=True):
    """ Show main MTT UI

    :param toggle: (bool) if False, UI will be deleted before a new one be shown
    """
    from mttView import show_ui
    show_ui(toggle=toggle)


def create_nodes(define_path=None, define_type=None):
    """ Create new shading node by selecting texture files

    :param define_path: (string) default folder path
    :param define_type: (string) default texture node type
    """
    from mttFilterFileDialog import create_nodes
    create_nodes(define_path=define_path, define_type=define_type)


def override_panels(custom_hs_cmd=None, custom_ne_cmd=None):
    """ Override panels creation to add custom buttons

    :param custom_hs_cmd: (bool) Override HyperShade if True
    :param custom_ne_cmd: (bool)Override Node Editor if True
    """
    from mttOverridePanels import override_panels
    override_panels(custom_hs_cmd=custom_hs_cmd, custom_ne_cmd=custom_ne_cmd)
