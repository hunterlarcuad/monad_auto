import os # noqa
import sys # noqa
import argparse
import random
import time
import copy
import pdb # noqa
import shutil
import math
import re
from datetime import datetime

from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
from DrissionPage._elements.none_element import NoneElement
# from DrissionPage.common import Keys
# from DrissionPage import Chromium
# from DrissionPage.common import Actions
# from DrissionPage.common import Settings

from fun_utils import ding_msg
from fun_utils import get_date
from fun_utils import load_file
from fun_utils import save2file
from fun_utils import format_ts
from fun_utils import extract_numbers

from conf import DEF_LOCAL_PORT
from conf import DEF_INCOGNITO
from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_NUM_TRY
from conf import NUM_MAX_TRY_PER_DAY
from conf import DEF_DING_TOKEN
from conf import DEF_PATH_BROWSER
from conf import DEF_PATH_DATA_STATUS
from conf import DEF_HEADER_STATUS
from conf import DEF_OKX_EXTENSION_PATH
from conf import EXTENSION_ID_OKX
from conf import DEF_PWD
from conf import DEF_SEND_AMOUNT_MIN
from conf import DEF_SEND_AMOUNT_MAX
from conf import MAGICEDEN_CA

from conf import DEF_PATH_DATA_PURSE
from conf import DEF_HEADER_PURSE

from conf import TZ_OFFSET
from conf import DEL_PROFILE_DIR

from conf import logger

"""
2025.03.07
NFT Mint on magiceden.io
"""

# Wallet balance
DEF_INSUFFICIENT = -1
DEF_SUCCESS = 0
DEF_FAIL = 1

# Mint would exceed wallet limit
DEF_EXCEED_LIMIT = 10

# output
IDX_NUM_MINT = 1
IDX_DATE_TX = 2
IDX_NUM_TRY = 3
IDX_UPDATE = 4
FIELD_NUM = IDX_UPDATE + 1


class MonadTask():
    def __init__(self) -> None:
        self.args = None
        self.page = None
        self.s_today = get_date(is_utc=True)
        self.file_proxy = None

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

        # 是否有更新
        self.is_update = False

        # 账号执行情况
        self.dic_status = {}

        self.dic_purse = {}

        self.purse_load()

    def set_args(self, args):
        self.args = args
        self.is_update = False

        # created tx
        self.is_created_tx = False

        self.n_points_spin = -1
        self.n_points = -1
        self.n_referrals = -1
        self.n_completed = -1

    def __del__(self):
        self.status_save()

    def purse_load(self):
        self.file_purse = f'{DEF_PATH_DATA_PURSE}/purse.csv'
        self.dic_purse = load_file(
            file_in=self.file_purse,
            idx_key=0,
            header=DEF_HEADER_PURSE
        )

    def status_load(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def status_save(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status.csv'
        save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            if self.page:
                try:
                    self.page.quit()
                except Exception as e:
                    logger.info(f'[Close] Error: {e}')

    def initChrome(self, s_profile):
        """
        s_profile: 浏览器数据用户目录名称
        """
        # Settings.singleton_tab_obj = True

        profile_path = s_profile

        # 是否设置无痕模式
        if DEF_INCOGNITO:
            co = ChromiumOptions().incognito(True)
        else:
            co = ChromiumOptions()

        # 设置本地启动端口
        co.set_local_port(port=DEF_LOCAL_PORT)
        if len(DEF_PATH_BROWSER) > 0:
            co.set_paths(browser_path=DEF_PATH_BROWSER)

        co.set_argument('--accept-lang', 'en-US')  # 设置语言为英语（美国）
        co.set_argument('--lang', 'en-US')

        # 阻止“自动保存密码”的提示气泡
        co.set_pref('credentials_enable_service', False)

        # 阻止“要恢复页面吗？Chrome未正确关闭”的提示气泡
        co.set_argument('--hide-crash-restore-bubble')

        # 关闭沙盒模式
        # co.set_argument('--no-sandbox')

        # popups支持的取值
        # 0：允许所有弹窗
        # 1：只允许由用户操作触发的弹窗
        # 2：禁止所有弹窗
        # co.set_pref(arg='profile.default_content_settings.popups', value='0')

        co.set_user_data_path(path=DEF_PATH_USER_DATA)
        co.set_user(user=profile_path)

        # 获取当前工作目录
        current_directory = os.getcwd()

        # 检查目录是否存在
        if os.path.exists(os.path.join(current_directory, DEF_OKX_EXTENSION_PATH)): # noqa
            logger.info(f'okx plugin path: {DEF_OKX_EXTENSION_PATH}')
            co.add_extension(DEF_OKX_EXTENSION_PATH)
        else:
            print("okx plugin directory is not exist. Exit!")
            sys.exit(1)

        # https://drissionpage.cn/ChromiumPage/browser_opt
        co.headless(DEF_USE_HEADLESS)
        co.set_user_agent(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36') # noqa

        try:
            self.page = ChromiumPage(co)
        except Exception as e:
            logger.info(f'Error: {e}')
        finally:
            pass

        self.page.wait.load_start()
        # self.page.wait(2)

        # tab_new = self.page.new_tab()
        # self.page.close_tabs(tab_new, others=True)

        # 浏览器启动时有 okx 弹窗，关掉
        # self.check_start_tabs()

    def logit(self, func_name=None, s_info=None):
        s_text = f'{self.args.s_profile}'
        if func_name:
            s_text += f' [{func_name}]'
        if s_info:
            s_text += f' {s_info}'
        logger.info(s_text)

    def close_popup_tabs(self, s_keep='OKX Web3'):
        # 关闭 OKX 弹窗
        if len(self.page.tab_ids) > 1:
            self.logit('close_popup_tabs', None)
            n_width_max = -1
            for tab_id in self.page.tab_ids:
                n_width_tab = self.page.get_tab(tab_id).rect.size[0]
                if n_width_max < n_width_tab:
                    n_width_max = n_width_tab

            tab_ids = self.page.tab_ids
            n_tabs = len(tab_ids)
            for i in range(n_tabs-1, -1, -1):
                tab_id = tab_ids[i]
                n_width_tab = self.page.get_tab(tab_id).rect.size[0]
                if n_width_tab < n_width_max:
                    s_title = self.page.get_tab(tab_id).title
                    self.logit(None, f'Close tab:{s_title} width={n_width_tab} < {n_width_max}') # noqa
                    self.page.get_tab(tab_id).close()
                    return True
        return False

    def is_exist(self, s_title, s_find, match_type):
        b_ret = False
        if match_type == 'fuzzy':
            if s_title.find(s_find) >= 0:
                b_ret = True
        else:
            if s_title == s_find:
                b_ret = True

        return b_ret

    def check_start_tabs(self, s_keep='新标签页', match_type='fuzzy'):
        """
        关闭多余的标签页
        match_type
            precise 精确匹配
            fuzzy 模糊匹配
        """
        if self.page.tabs_count > 1:
            self.logit('check_start_tabs', None)
            tab_ids = self.page.tab_ids
            n_tabs = len(tab_ids)
            for i in range(n_tabs-1, -1, -1):
                tab_id = tab_ids[i]
                s_title = self.page.get_tab(tab_id).title
                # print(f's_title={s_title}')
                if self.is_exist(s_title, s_keep, match_type):
                    continue
                if len(self.page.tab_ids) == 1:
                    break
                self.logit(None, f'Close tab:{s_title}')
                self.page.get_tab(tab_id).close()
            self.logit(None, f'Keeped tab: {self.page.title}')
            return True
        return False

    def okx_secure_wallet(self):
        # Secure your wallet
        ele_info = self.page.ele('Secure your wallet')
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_secure_wallet', 'Secure your wallet')
            ele_btn = self.page.ele('Password', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)
                self.logit('okx_secure_wallet', 'Select Password')

                # Next
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                    self.logit('okx_secure_wallet', 'Click Next')
                    return True
        return False

    def okx_set_pwd(self):
        # Set password
        ele_info = self.page.ele('Set password', timeout=2)
        if not isinstance(ele_info, NoneElement):
            self.logit('okx_set_pwd', 'Set Password')
            ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit('okx_set_pwd', 'Input Password')
                self.page.actions.move_to(ele_input).click().type(DEF_PWD)
            self.page.wait(1)
            ele_input = self.page.ele('@@tag()=input@@data-testid=okd-input@@placeholder:Re-enter', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.page.actions.move_to(ele_input).click().type(DEF_PWD)
                self.logit('okx_set_pwd', 'Re-enter Password')
            self.page.wait(1)
            ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.logit('okx_set_pwd', 'Password Confirmed [OK]')
                self.page.wait(10)
                return True
        return False

    def okx_bulk_import_private_key(self, s_key):
        ele_btn = self.page.ele('@@tag()=div@@class:_typography@@text():Bulk import private key', timeout=2) # noqa
        if not isinstance(ele_btn, NoneElement):
            ele_btn.click(by_js=True)
            self.logit('okx_bulk_import_private_key', 'Click ...')

            self.page = self.page.get_tab(self.page.latest_tab.tab_id)

            ele_btn = self.page.ele('@@tag()=i@@id=okdDialogCloseBtn', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Close pwd input box ...')
                ele_btn.click(by_js=True)

            ele_btn = self.page.ele('@@tag()=div@@data-testid=okd-select-reference-value-box', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Select network ...')
                ele_btn.click(by_js=True)

            ele_btn = self.page.ele('@@tag()=div@@class:_typography@@text()=EVM networks', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                self.logit(None, 'Click EVM networks ...')
                ele_btn.click(by_js=True)

            ele_input = self.page.ele('@@tag()=textarea@@id:pk-input@@placeholder:private', timeout=2) # noqa
            if not isinstance(ele_input, NoneElement):
                self.logit(None, 'Click EVM networks ...')
                self.page.actions.move_to(ele_input).click().type(s_key) # noqa
                self.page.wait(5)

    def init_okx(self, is_bulk=False):
        """
        chrome-extension://jiofmdifioeejeilfkpegipdjiopiekl/popup/index.html
        """
        # self.check_start_tabs()
        s_url = f'chrome-extension://{EXTENSION_ID_OKX}/home.html'
        self.page.get(s_url)
        # self.page.wait.load_start()
        self.page.wait(3)
        self.close_popup_tabs()
        self.check_start_tabs('OKX Wallet', 'precise')

        self.logit('init_okx', f'tabs_count={self.page.tabs_count}')

        self.save_screenshot(name='okx_1.jpg')

        ele_info = self.page.ele('@@tag()=div@@class:balance', timeout=2) # noqa
        if not isinstance(ele_info, NoneElement):
            s_info = ele_info.text
            self.logit('init_okx', f'Account balance: {s_info}') # noqa
            return True

        ele_btn = self.page.ele('Import wallet', timeout=2)
        if not isinstance(ele_btn, NoneElement):
            # Import wallet
            self.logit('init_okx', 'Import wallet ...')
            ele_btn.click(by_js=True)

            self.page.wait(1)
            ele_btn = self.page.ele('Seed phrase or private key', timeout=2)
            if not isinstance(ele_btn, NoneElement):
                # Import wallet
                self.logit('init_okx', 'Select Seed phrase or private key ...') # noqa
                ele_btn.click(by_js=True)
                self.page.wait(1)

                s_key = self.dic_purse[self.args.s_profile][1]
                if len(s_key.split()) == 1:
                    # Private key
                    self.logit('init_okx', 'Import By Private key')
                    ele_btn = self.page.ele('Private key', timeout=2)
                    if not isinstance(ele_btn, NoneElement):
                        # 点击 Private key Button
                        self.logit('init_okx', 'Select Private key')
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                        ele_input = self.page.ele('@class:okui-input-input input-textarea ta', timeout=2) # noqa
                        if not isinstance(ele_input, NoneElement):
                            # 使用动作，输入完 Confirm 按钮才会变成可点击状态
                            self.page.actions.move_to(ele_input).click().type(s_key) # noqa
                            self.page.wait(5)
                            self.logit('init_okx', 'Input Private key')
                    is_bulk = True
                    if is_bulk:
                        self.okx_bulk_import_private_key(s_key)
                else:
                    # Seed phrase
                    self.logit('init_okx', 'Import By Seed phrase')
                    words = s_key.split()

                    # 输入助记词需要最大化窗口，否则最后几个单词可能无法输入
                    self.page.set.window.max()

                    ele_inputs = self.page.eles('.mnemonic-words-inputs__container__input', timeout=2) # noqa
                    if not isinstance(ele_inputs, NoneElement):
                        self.logit('init_okx', 'Input Seed phrase')
                        for i in range(len(ele_inputs)):
                            ele_input = ele_inputs[i]
                            self.page.actions.move_to(ele_input).click().type(words[i]) # noqa
                            self.logit(None, f'Input word [{i+1}/{len(words)}]') # noqa
                            self.page.wait(1)

                # Confirm
                max_wait_sec = 10
                i = 1
                while i < max_wait_sec:
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
                    self.logit('init_okx', f'To Confirm ... {i}/{max_wait_sec}') # noqa
                    if not isinstance(ele_btn, NoneElement):
                        if ele_btn.states.is_enabled is False:
                            self.logit(None, 'Confirm Button is_enabled=False')
                        else:
                            if ele_btn.states.is_clickable:
                                ele_btn.click(by_js=True)
                                self.logit('init_okx', 'Confirm Button is clicked') # noqa
                                self.page.wait(1)
                                break
                            else:
                                self.logit(None, 'Confirm Button is_clickable=False') # noqa

                    i += 1
                    self.page.wait(1)
                # 未点击 Confirm
                if i >= max_wait_sec:
                    self.logit('init_okx', 'Confirm Button is not found [ERROR]') # noqa

                # 导入私钥有此选择页面，导入助记词则没有此选择过程
                # Select network and Confirm
                ele_info = self.page.ele('Select network', timeout=2)
                if not isinstance(ele_info, NoneElement):
                    self.logit('init_okx', 'Select network ...')
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                        self.logit('init_okx', 'Select network finish')

                self.okx_secure_wallet()

                # Set password
                is_success = self.okx_set_pwd()

                # Start your Web3 journey
                self.page.wait(1)
                self.save_screenshot(name='okx_2.jpg')
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Start', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.logit('init_okx', 'import wallet success')
                    self.save_screenshot(name='okx_3.jpg')
                    self.page.wait(2)

                if is_success:
                    return True
        else:
            ele_info = self.page.ele('Your portal to Web3', timeout=2)
            if not isinstance(ele_info, NoneElement):
                self.logit('init_okx', 'Input password to unlock ...')
                s_path = '@@tag()=input@@data-testid=okd-input@@placeholder:Enter' # noqa
                ele_input = self.page.ele(s_path, timeout=2) # noqa
                if not isinstance(ele_input, NoneElement):
                    self.page.actions.move_to(ele_input).click().type(DEF_PWD)
                    if ele_input.value != DEF_PWD:
                        self.logit('init_okx', '[ERROR] Fail to input passwrod !') # noqa
                        self.page.set.window.max()
                        return False

                    self.page.wait(1)
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Unlock', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)

                        self.logit('init_okx', 'login success')
                        self.save_screenshot(name='okx_2.jpg')

                        return True
            else:
                ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                else:
                    ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        ele_btn.click(by_js=True)
                        self.page.wait(1)
                    else:
                        self.logit('init_okx', '[ERROR] What is this ... [quit]') # noqa
                        self.page.quit()

        self.logit('init_okx', 'login failed [ERROR]')
        return False

    def save_screenshot(self, name):
        # 对整页截图并保存
        # self.page.set.window.max()
        s_name = f'{self.args.s_profile}_{name}'
        self.page.get_screenshot(path='tmp_img', name=s_name, full_page=True)

    def is_task_complete(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        if s_profile not in self.dic_status:
            return False

        claimed_date = self.dic_status[s_profile][idx_status]
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET) # noqa
        if date_now != claimed_date:
            return False
        else:
            return True

    def update_status(self, idx_status, s_value):
        update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        def init_status():
            self.dic_status[self.args.s_profile] = [
                self.args.s_profile,
            ]
            for i in range(1, FIELD_NUM):
                self.dic_status[self.args.s_profile].append('')

        if self.args.s_profile not in self.dic_status:
            init_status()
        if len(self.dic_status[self.args.s_profile]) != FIELD_NUM:
            init_status()
        if self.dic_status[self.args.s_profile][idx_status] == s_value:
            return

        self.dic_status[self.args.s_profile][idx_status] = s_value
        self.dic_status[self.args.s_profile][IDX_UPDATE] = update_time

        self.status_save()
        self.is_update = True

    def update_date(self, idx_status, update_ts=None):
        if not update_ts:
            update_ts = time.time()
        update_time = format_ts(update_ts, 2, TZ_OFFSET)

        claim_date = update_time[:10]

        self.update_status(idx_status, claim_date)

    def get_status_by_idx(self, idx_status, s_profile=None):
        if s_profile is None:
            s_profile = self.args.s_profile

        s_val = ''
        lst_pre = self.dic_status.get(s_profile, [])
        if len(lst_pre) == FIELD_NUM:
            try:
                s_val = int(lst_pre[idx_status])
            except: # noqa
                pass

        return s_val

    def get_pre_num_try(self, s_profile=None):
        num_try_pre = 0

        s_val = self.get_status_by_idx(IDX_NUM_TRY, s_profile)

        try:
            num_try_pre = int(s_val)
        except: # noqa
            pass

        return num_try_pre

    def update_num_try(self, s_profile=None):
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET)
        s_update = self.get_status_by_idx(-1, s_profile)
        if len(s_update) > 10:
            date_update = s_update[:10]
        else:
            date_update = ''
        if date_now != date_update:
            num_try_cur = 1
        else:
            num_try_pre = self.get_pre_num_try(s_profile)
            num_try_cur = num_try_pre + 1

        self.update_status(IDX_NUM_TRY, str(num_try_cur))

    def wait_cofirm(self, n_wait_sec=10):
        """
        wait until max_wait_sec or the popup window disappear
        """
        # n_wait_sec = 10
        j = 0
        while j < n_wait_sec:
            j += 1
            self.page.wait(1)
            self.logit(None, f'Wait {j}/{n_wait_sec}')

            if len(self.page.tab_ids) != 2:
                break

    def monad_auto_login(self):
        """
        """
        for i in range(1, DEF_NUM_TRY+1):
            self.logit('monad_auto_login', f'try_i={i}/{DEF_NUM_TRY}')

            if i >= DEF_NUM_TRY/2:
                is_bulk = True
            else:
                is_bulk = False
            if self.init_okx(is_bulk) is False:
                continue

            ele_btn = self.page.ele('@@tag()=button@@data-testid=okd-button@@text():Cancel', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)
                self.logit(None, 'Cancel Unknown transaction')

            s_url = f'https://magiceden.io/mint-terminal/monad-testnet/{MAGICEDEN_CA}'
            self.page.get(s_url)
            # self.page.wait.load_start()
            self.page.wait(3)

            self.logit('monad_auto_login', f'tabs_count={self.page.tabs_count}')

            # 钱包连接状态
            ele_btn = self.page.ele('@@tag()=button@@data-test-id=wallet-connect-button', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                s_info = ele_btn.text
                if 'Log In' == s_info:
                    self.logit(None, 'Need to Connect Wallet ...') # noqa
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                    ele_btn = self.page.eles('@@tag()=div@@data-testid=dynamic-modal-shadow@@class=dynamic-shadow-dom', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        tab_shadow = ele_btn[0].shadow_root
                        ele_btn = tab_shadow.ele('@@tag()=button@@class=list-item-button list-tile', timeout=2) # noqa
                        if not isinstance(ele_btn, NoneElement):
                            ele_btn.click(by_js=True)
                            self.page.wait(2)

                            ele_btn = tab_shadow.ele('@@tag()=div@@class=list-tile__children@@text()=OKX Wallet', timeout=2) # noqa
                            if not isinstance(ele_btn, NoneElement):
                                ele_btn.click(by_js=True)
                                self.page.wait(2)

                            ele_btn = tab_shadow.ele('@@tag()=div@@class=list-tile__children@@text()=EVM', timeout=2) # noqa
                            if not isinstance(ele_btn, NoneElement):
                                ele_btn.click(by_js=True)
                                self.page.wait(2)
            else:
                # 钱包已连接
                self.logit(None, 'Wallet is connected')
                return True


            # OKX Wallet Connect
            self.save_screenshot(name='page_wallet_connect.jpg')
            if len(self.page.tab_ids) == 2:
                tab_id = self.page.latest_tab
                tab_new = self.page.get_tab(tab_id)
                ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Connect', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(2)

            # OKX Wallet Signature request
            self.save_screenshot(name='page_wallet_signature.jpg')
            if len(self.page.tab_ids) == 2:
                self.logit(None, 'OKX Wallet Signature request ...') # noqa
                tab_id = self.page.latest_tab
                tab_new = self.page.get_tab(tab_id)
                ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.wait_cofirm()
                    self.logit(None, 'OKX Wallet Signature request Confirmed [OK]') # noqa

                    return True

            # OKX Wallet Add network
            if len(self.page.tab_ids) == 2:
                self.logit(None, 'OKX Wallet Add network ...') # noqa
                tab_id = self.page.latest_tab
                tab_new = self.page.get_tab(tab_id)
                ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text()=Approve', timeout=2) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(1)
                    continue

        self.logit(None, 'Wallet is failed to connected [ERROR]') # noqa

        return False

    def okx_cancel(self):
        # OKX Wallet Cancel Uncomplete request
        if len(self.page.tab_ids) == 2:
            tab_id = self.page.latest_tab
            tab_new = self.page.get_tab(tab_id)
            ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Cancel', timeout=2) # noqa
            if not isinstance(ele_btn, NoneElement):
                ele_btn.click(by_js=True)
                self.page.wait(1)
                self.logit(None, 'Uncomplete request. Cancel')

    def mint_one(self):
        """
        """
        self.okx_cancel()
        for i in range(1, DEF_NUM_TRY+1):
            self.logit('mint', f'try_i={i}/{DEF_NUM_TRY}')
            # pdb.set_trace()

            ele_btn = self.page.ele('@@tag()=button@@class:tw@@text()=Mint', timeout=1) # noqa
            if not isinstance(ele_btn, NoneElement):
                if ele_btn.states.is_enabled is False:
                    ele_info = self.page.ele('@@tag()=div@@class:tw-text-yellow-error', timeout=1) # noqa
                    if not isinstance(ele_info, NoneElement):
                        s_info = ele_info.text
                        self.logit(None, f'Fail to mint. msg: {s_info}') # noqa
                        # Mint would exceed wallet limit, you can mint 1 NFTs in total.
                        if s_info.find('exceed') >= 0:
                            self.update_date(IDX_DATE_TX)
                            self.update_status(IDX_NUM_MINT, 1)
                            return DEF_EXCEED_LIMIT

                else:
                    ele_btn.click(by_js=True)

                max_wait_sec = 10
                i = 0
                while i < max_wait_sec:
                    i += 1
                    if len(self.page.tab_ids) == 2:
                        break
                    self.page.wait(1)
                    self.logit(None, f'Wait Confirm window ... {i}/{max_wait_sec}') # noqa

                # Confirm
                if len(self.page.tab_ids) == 2:
                    tab_id = self.page.latest_tab
                    tab_new = self.page.get_tab(tab_id)
                    ele_btn = tab_new.ele('@@tag()=button@@data-testid=okd-button@@text():Confirm', timeout=2) # noqa
                    if not isinstance(ele_btn, NoneElement):
                        i = 0
                        while i < max_wait_sec:
                            i += 1
                            if ele_btn.states.is_enabled is True:
                                break
                            self.page.wait(1)
                            self.logit(None, f'Wait Confirm Button ... {i}/{max_wait_sec}') # noqa
                        ele_btn.click(by_js=True)
                        self.wait_cofirm()
                        self.logit(None, 'Confirm transaction [OK]')
                        self.update_date(IDX_DATE_TX)
                        self.update_status(IDX_NUM_MINT, 1)
                        return DEF_SUCCESS
            else:
                ele_btn = self.page.ele('@@tag()=button@@class:tw@@text()=Switch to Monad Testnet', timeout=1) # noqa
                if not isinstance(ele_btn, NoneElement):
                    ele_btn.click(by_js=True)
                    self.page.wait(2)

        return DEF_FAIL

    def monad_auto_run(self):
        self.update_num_try()

        if not self.monad_auto_login():
            return False

        DEF_NUM = 1
        for i in range(DEF_NUM):
            self.logit('mint', f'run i={i}/{DEF_NUM}')
            self.mint_one()

        # self.update_status(IDX_NUM_SHARD, amount_shard)

        self.logit('monad_auto_run', 'Finished!')
        self.close()

        return True


def send_msg(instMonadTask, lst_success):
    if len(DEF_DING_TOKEN) > 0 and len(lst_success) > 0:
        s_info = ''
        for s_profile in lst_success:
            lst_status = None
            if s_profile in instMonadTask.dic_status:
                lst_status = instMonadTask.dic_status[s_profile]

            if lst_status is None:
                lst_status = [s_profile, -1]

            s_info += '- {} {}\n'.format(
                s_profile,
                lst_status[1],
            )
        d_cont = {
            'title': 'Daily Active Finished! [monad_auto]',
            'text': (
                'Daily Active [monad_auto]\n'
                '- {}\n'
                '{}\n'
                .format(DEF_HEADER_STATUS, s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if DEL_PROFILE_DIR and os.path.exists(DEF_PATH_USER_DATA):
        logger.info(f'Delete {DEF_PATH_USER_DATA} ...')
        shutil.rmtree(DEF_PATH_USER_DATA)
        logger.info(f'Directory {DEF_PATH_USER_DATA} is deleted') # noqa

    instMonadTask = MonadTask()

    if len(args.profile) > 0:
        items = args.profile.split(',')
    else:
        # 从配置文件里获取钱包名称列表
        items = list(instMonadTask.dic_purse.keys())

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(profiles)
    n = 0

    lst_success = []

    def is_complete(lst_status):
        b_ret = True
        date_now = format_ts(time.time(), style=1, tz_offset=TZ_OFFSET)

        if lst_status:
            for idx_status in [IDX_DATE_TX]:
                claimed_date = lst_status[idx_status]
                if date_now != claimed_date:
                    b_ret = b_ret and False
            date_update = lst_status[-1][:10]
        else:
            date_update = None
            b_ret = False

        num_try_pre = instMonadTask.get_pre_num_try(s_profile)
        if (date_update == date_now) and (num_try_pre == NUM_MAX_TRY_PER_DAY):
            b_ret = True

        return b_ret

    # 将已完成的剔除掉
    instMonadTask.status_load()
    # 从后向前遍历列表的索引
    for i in range(len(profiles) - 1, -1, -1):
        s_profile = profiles[i]
        if s_profile in instMonadTask.dic_status:
            lst_status = instMonadTask.dic_status[s_profile]
            if is_complete(lst_status):
                n += 1
                profiles.pop(i)
        else:
            continue
    logger.info('#'*40)
    percent = math.floor((n / total) * 100)
    logger.info(f'Progress: {percent}% [{n}/{total}]') # noqa

    while profiles:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(profiles)
        percent = math.floor((n / total) * 100)
        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile}]') # noqa
        profiles.remove(s_profile)

        args.s_profile = s_profile

        if s_profile not in instMonadTask.dic_purse:
            logger.info(f'{s_profile} is not in purse conf [ERROR]')
            sys.exit(0)

        def _run():
            s_directory = f'{DEF_PATH_USER_DATA}/{args.s_profile}'
            if os.path.exists(s_directory) and os.path.isdir(s_directory):
                pass
            else:
                # Create new profile
                instMonadTask.initChrome(args.s_profile)
                instMonadTask.init_okx()
                instMonadTask.close()

            instMonadTask.initChrome(args.s_profile)
            is_claim = instMonadTask.monad_auto_run()
            return is_claim

        # 如果出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                is_claim = False
                if j > 1:
                    logger.info(f'⚠️ 正在重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa

                instMonadTask.set_args(args)
                instMonadTask.status_load()

                if s_profile in instMonadTask.dic_status:
                    lst_status = instMonadTask.dic_status[s_profile]
                else:
                    lst_status = None

                is_claim = False
                is_ready_claim = True
                if is_complete(lst_status):
                    logger.info(f'[{s_profile}] Last update at {lst_status[IDX_UPDATE]}') # noqa
                    is_ready_claim = False
                    break
                if is_ready_claim:
                    is_claim = _run()

                if is_claim:
                    lst_success.append(s_profile)
                    instMonadTask.close()
                    break

            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                instMonadTask.close()
                if j < max_try_except:
                    time.sleep(5)

        if instMonadTask.is_update is False:
            continue

        logger.info(f'Progress: {percent}% [{n}/{total}] [{s_profile} Finish]')

        if len(items) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)

    send_msg(instMonadTask, lst_success)


if __name__ == '__main__':
    """
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--loop_interval', required=False, default=60, type=int,
        help='[默认为 60] 执行完一轮 sleep 的时长(单位是秒)，如果是0，则不循环，只执行一次'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    args = parser.parse_args()
    if args.loop_interval <= 0:
        main(args)
    else:
        while True:
            main(args)
            logger.info('#####***** Loop sleep {} seconds ...'.format(args.loop_interval)) # noqa
            time.sleep(args.loop_interval)

"""
python monad_auto.py --sleep_sec_min=30 --sleep_sec_max=60 --loop_interval=60
python monad_auto.py --sleep_sec_min=600 --sleep_sec_max=1800 --loop_interval=60
python monad_auto.py --sleep_sec_min=60 --sleep_sec_max=180
"""
