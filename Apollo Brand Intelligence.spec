# -*- mode: python ; coding: utf-8 -*-
"""
Apollo Brand Intelligence Enterprise Specification for PyInstaller.
Bundles Apollo Brand Intelligence and Artemis Dual Executables.
"""

import os

REPO_ROOT = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(REPO_ROOT, 'apollo.ico'), '.'),
    (os.path.join(REPO_ROOT, 'apollo.png'), '.'),
    (os.path.join(REPO_ROOT, 'artemis.ico'), '.'),
    (os.path.join(REPO_ROOT, 'artemis.png'), '.')
]

subpackages = [
    os.path.join(REPO_ROOT, 'apollo'),
    os.path.join(REPO_ROOT, 'apollo', 'core'),
    os.path.join(REPO_ROOT, 'apollo', 'ui'),
    os.path.join(REPO_ROOT, 'apollo', 'ui', 'modals'),
    os.path.join(REPO_ROOT, 'apollo', 'ui', 'components'),
    os.path.join(REPO_ROOT, 'apollo', 'scrapers'),
    os.path.join(REPO_ROOT, 'apollo', 'scrapers', 'engines'),
    os.path.join(REPO_ROOT, 'apollo', 'export'),
    os.path.join(REPO_ROOT, 'apollo', 'compliance')
]

hidden_imports_apollo = [
    'PIL', 'PIL.ImageTk', 'openpyxl', 'bs4', 'requests', 'curl_cffi',
    'curl_cffi.requests', 'playwright', 'playwright.sync_api',
    'apollo', 'apollo.core', 'apollo.core.contracts', 'apollo.core.data_store',
    'apollo.core.session_vault', 'apollo.core.visual_catalog',
    'apollo.core.visual_harvester', 'apollo.core.syndicate_graph',
    'apollo.core.intel_pack_manager', 'apollo.core.voice_controller',
    'apollo.core.api_client',
    'apollo.ui', 'apollo.ui.theme_engine', 'apollo.ui.theme_definitions',
    'apollo.ui.dialogs', 'apollo.ui.components.tooltip',
    'apollo.ui.modals.brand_registry_modal', 'apollo.ui.modals.dossier_manager_modal',
    'apollo.ui.modals.field_guide_modal', 'apollo.ui.modals.multi_sector_modal',
    'apollo.ui.modals.product_type_modal', 'apollo.ui.modals.session_vault_modal',
    'apollo.ui.modals.syndicate_hunter_modal', 'apollo.ui.modals.system_diagnostics',
    'apollo.ui.modals.vero_disclosure_modal', 'apollo.ui.modals.visual_catalog_modal',
    'apollo.scrapers', 'apollo.scrapers.registry', 'apollo.scrapers.batch_importer',
    'apollo.scrapers.engines.scraper', 'apollo.scrapers.engines.aliexpress_scraper',
    'apollo.scrapers.engines.wish_scraper', 'apollo.scrapers.engines.temu_scraper',
    'apollo.scrapers.engines.mercadolibre_scraper', 'apollo.scrapers.engines.redbubble_scraper',
    'apollo.scrapers.engines.printerval_scraper', 'apollo.scrapers.engines.printblur_scraper',
    'apollo.scrapers.engines.vinted_scraper', 'apollo.scrapers.engines.tiktok_scraper',
    'apollo.scrapers.engines.manomano_scraper', 'apollo.scrapers.engines.scribd_scraper',
    'apollo.scrapers.engines.teepublic_scraper', 'apollo.scrapers.engines.etsy_scraper',
    'apollo.scrapers.engines.spreadshirt_scraper', 'apollo.scrapers.engines.zazzle_scraper',
    'apollo.scrapers.engines.cafepress_scraper', 'apollo.scrapers.engines.threadless_scraper',
    'apollo.scrapers.engines.teespring_scraper', 'apollo.scrapers.engines.fineartamerica_scraper',
    'apollo.scrapers.engines.shopify_scraper',
    'apollo.export', 'apollo.export.exporter', 'apollo.export.vero_parser',
    'apollo.export.vero_pdf_parser', 'pypdf',
    'apollo.compliance', 'apollo.compliance.artemis', 'apollo.compliance.artemis_bridge',
    'apollo.compliance.artemis_data_store', 'apollo.compliance.artemis_engine',
    'apollo.compliance.argus_engine', 'apollo.compliance.argus_compliance_modal',
    # Bare import aliases for backward compatibility
    'scraper', 'aliexpress_scraper', 'wish_scraper', 'temu_scraper',
    'mercadolibre_scraper', 'redbubble_scraper', 'printerval_scraper',
    'printblur_scraper', 'vinted_scraper', 'tiktok_scraper', 'manomano_scraper',
    'scribd_scraper', 'teepublic_scraper', 'etsy_scraper', 'spreadshirt_scraper',
    'zazzle_scraper', 'cafepress_scraper', 'threadless_scraper', 'teespring_scraper',
    'fineartamerica_scraper', 'shopify_scraper', 'exporter', 'vero_parser',
    'vero_pdf_parser', 'argus_engine', 'argus_compliance_modal',
    'artemis', 'artemis_bridge', 'artemis_data_store', 'artemis_engine',
    'data_store', 'session_vault', 'visual_catalog', 'visual_harvester',
    'syndicate_graph', 'intel_pack_manager', 'voice_controller',
    'brand_registry_modal', 'dossier_manager_modal', 'field_guide_modal',
    'multi_sector_modal', 'product_type_modal', 'session_vault_modal',
    'syndicate_hunter_modal', 'system_diagnostics', 'vero_disclosure_modal',
    'visual_catalog_modal', 'tooltip', 'batch_importer', 'theme_definitions'
]

a_apollo = Analysis(
    ['run_apollo.py'],
    pathex=subpackages,
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports_apollo,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz_apollo = PYZ(a_apollo.pure)

exe_apollo = EXE(
    pyz_apollo,
    a_apollo.scripts,
    [],
    exclude_binaries=True,
    name='Apollo Brand Intelligence',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(REPO_ROOT, 'apollo.ico')],
)

hidden_imports_artemis = [
    'PIL', 'PIL.ImageTk', 'requests', 'curl_cffi', 'playwright',
    'apollo.compliance.artemis_bridge', 'apollo.compliance.artemis_data_store',
    'apollo.compliance.artemis_engine', 'apollo.ui.theme_definitions',
    'artemis_bridge', 'artemis_data_store', 'artemis_engine', 'theme_definitions'
]

a_artemis = Analysis(
    [os.path.join('apollo', 'compliance', 'artemis.py')],
    pathex=subpackages,
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports_artemis,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz_artemis = PYZ(a_artemis.pure)

exe_artemis = EXE(
    pyz_artemis,
    a_artemis.scripts,
    [],
    exclude_binaries=True,
    name='Artemis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(REPO_ROOT, 'artemis.ico')],
)

coll = COLLECT(
    exe_apollo,
    a_apollo.binaries,
    a_apollo.datas,
    exe_artemis,
    a_artemis.binaries,
    a_artemis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Apollo Brand Intelligence',
)
