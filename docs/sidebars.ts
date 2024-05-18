import type { SidebarsConfig } from '@docusaurus/plugin-content-docs';

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'index',
    {
      type: 'category',
      label: 'rawtypes',
      link: { type: 'doc', id: 'rawtypes/index' },
      items: [
        'rawtypes/args',
        'rawtypes/result',
      ],
    },
    {
      type: 'category',
      label: 'cindex.index',
      link: { type: 'doc', id: 'cindex/index' },
      items: [
        'cindex/python_module',
        'cindex/get_tu',
        'cindex/traverse',
        'cindex/cursor_kind/index',
        'cindex/type/index',
      ]
    },
    {
      type: 'category',
      label: 'examples',
      items: [
        'examples/imgui',
      ]
    },
    {
      type: 'category',
      label: 'setup.py',
      link: { type: 'doc', id: 'setup/index' },
      items: [
        'setup/command/index',
        'setup/pypi',
        'setup/metadata',
      ]
    },
  ],
};

export default sidebars;
