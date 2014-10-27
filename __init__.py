""" Maya Texture Toolkit

Maya Texture Toolkit aims to help artist to manage and work easily with textures in Maya
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
cmds.evalDeferred("import dbMayaTextureToolkit.mttOverridePanels as orp;orp.override_panels()")


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
    "path_pattern":"E:\\CG_Projects\\Demo_MTT"
}

"""
# AUTHOR = u'David B\xf4le aka Bioeden'
# AUTHOR = 'David B%sle aka Bioeden' % unichr(244)
# AUTHOR = 'David Bole aka Bioeden'

__author__ = u'David Bole aka Bioeden'
__version__ = 1.01

import maya.cmds as cmds
if cmds.optionVar(query='MTT_version') < __version__:

    cmds.optionVar(fv=['MTT_version', __version__])

    import mttConfig
    reload(mttConfig)
    import mttResources
    reload(mttResources)
    import mttCustomWidget
    reload(mttCustomWidget)

    import mttQuickFilterManager
    reload(mttQuickFilterManager)
    import mtt
    reload(mtt)
    import mttView
    reload(mttView)
    import mttModel
    reload(mttModel)
    import mttProxy
    reload(mttProxy)
    import mttDelegate
    reload(mttDelegate)
    import mttViewer
    reload(mttViewer)
    import mttFilterFileDialog
    reload(mttFilterFileDialog)
    import mttImportPolicy
    reload(mttImportPolicy)
    import mttOverridePanels
    reload(mttOverridePanels)


# -------------------------------------------------------------------------------------------------------------------- #
# perform import for direct access
# -------------------------------------------------------------------------------------------------------------------- #
from mtt import show_ui
from mttFilterFileDialog import create_nodes
from mttOverridePanels import override_panels