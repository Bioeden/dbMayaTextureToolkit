from maya import cmds


def exec_import_policy(selection, node_name, file_name):
    """ Import policy example

    :param selection: (list) of selected objects
    :param node_name: (string) created shading node
    :param file_name: (string) texture file name
    """

    file_name = file_name.split('.')[0]

    if file_name.endswith('_DIF'):
        for obj in selection:
            if cmds.attributeQuery('color', node=obj, exists=True):
                cmds.connectAttr('%s.outColor' % node_name, '%s.color' % obj)

    elif file_name.endswith('_SPE'):
        for obj in selection:
            if cmds.attributeQuery('specularColor', node=obj, exists=True):
                cmds.connectAttr('%s.outColor' % node_name, '%s.specularColor' % obj)

    elif file_name.endswith('_NOR'):
        for obj in selection:
            if cmds.attributeQuery('normalCamera', node=obj, exists=True):
                # create bump node
                current_bump_node = cmds.shadingNode('bump2d', name='%s_bump' % node_name, asUtility=True)
                cmds.setAttr('%s.bumpInterp' % current_bump_node, 1)
                # connect nodes
                cmds.connectAttr('%s.outAlpha' % node_name, '%s.bumpValue' % current_bump_node)
                cmds.connectAttr('%s.outNormal' % current_bump_node, '%s.normalCamera' % obj)
