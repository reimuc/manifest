"""Steam清单获取工具 - 高性能异步版本"""

import sys
import winreg
from argparse import ArgumentParser, Namespace
from pathlib import Path
from time import sleep

from loguru import logger
from rich.console import Console
from rich.text import Text

from src.core.api_client import APIClient
from src.core.constants import Steam, VERSION
from src.services.file_service import FileService
from src.services.github_service import GitHubService
from src.services.steam_service import SteamService


def show_banner():
    """显示应用欢迎banner"""
    console = Console()

    banner_text = Text()
    banner_text.append(r"""
     ('-. .-.   ('-.  _  .-')   .-') _      ('-.
    ( OO )  / _(  OO)( \( -O ) (  OO) )    ( OO ).-.
    ,--. ,--.(,------.,------. /     '._   / . --. /
    |  | |  | |  .---'|   /`. '|'--...__)  | \-.  \
    |   .|  | |  |    |  /  | |'--.  .--'.-'-'  |  |
    |       |(|  '--. |  |_.' |   |  |    \| |_.'  |
    |  .-.  | |  `---.|  .  '.'   |  |     |  .-.  |
    |  | |  | |  `---.|  |\  \    |  |     |  | |  |
    `--' `--' `------'`--' '--'   `--'     `--' `--'
    """, style="bold magenta")

    content = Text.assemble(
        banner_text,
        "\n",
        (rf"🚀 Steam manifest v{VERSION}", "bold cyan"),
        "\n",
        (rf"💨 Powered by Python & AsyncIO", "dim white"),
        "\n"
    )

    console.print(content)


def init_logger(debug: bool = False):
    """初始化日志系统"""
    logger.remove()

    # 终端日志格式
    log_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<level>{message}</level>"
    )

    if debug:
        logger.add(sys.stderr, format=log_format, level="DEBUG")
    else:
        logger.add(sys.stderr, format=log_format, level="INFO")

    return logger


def init_command_args() -> Namespace:
    """初始化命令行参数"""
    parser = ArgumentParser(description="🚀 Steam 清单文件获取工具 v" + VERSION)
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s v{VERSION}")
    parser.add_argument("-a", "--appid", help="🎮 Steam 应用ID或名称")
    parser.add_argument("-k", "--key", help="🔑 GitHub API 访问密钥")
    parser.add_argument("-r", "--repo", help="📁 自定义 GitHub 仓库名称")
    parser.add_argument("-f", "--fixed", action="store_true", help="📌 启用固定清单模式")
    parser.add_argument("-d", "--debug", action="store_true", help="🔍 调试模式")
    return parser.parse_args()


def verify_steam_path() -> Path | None:
    """验证Steam安装路径"""
    try:
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, Steam.REG_PATH)
        steam_path = Path(winreg.QueryValueEx(hkey, Steam.REG_KEY)[0])

        if (steam_path / "steam.exe").exists():
            return steam_path

        return None
    except (FileNotFoundError, OSError):
        return None


async def main():
    """主程序入口"""
    show_banner()

    # 初始化
    args = init_command_args()
    init_logger(args.debug)

    # 验证Steam路径
    steam_path = verify_steam_path()
    if not steam_path:
        logger.error("❌ 未找到Steam安装路径")
        return

    logger.info(f"🎮 已定位Steam安装路径: {steam_path}")

    # 创建异步客户端和管理器
    async with APIClient() as api_client:
        try:
            # 初始化各个管理器
            file_processor = FileService()
            steam_service = SteamService(api_client)
            repo_manager = GitHubService(api_client, file_processor)

            # 获取应用ID
            if args.appid:
                app_query = args.appid
            else:
                sleep(0.5)
                app_query = Console().input("[cyan]请输入游戏名称或ID: [/cyan]")

            # 检查API速率限制 (移到用户输入之后，避免网络卡顿影响交互)
            if not await repo_manager.check_rate_limit():
                logger.error("❌ API请求次数已达上限，请稍后再试")
                return

            app_id = await steam_service.search_app(app_query)

            if not app_id:
                logger.error("❌ 无法获取应用ID")
                return

            app_id_str = str(app_id)

            # 构建仓库列表
            custom_repos = [args.repo] if args.repo else None

            # 查找仓库
            repo = await repo_manager.find_repository(app_id_str, custom_repos)

            if not repo:
                logger.error(f"❌ 未找到包含应用 {app_id_str} 的仓库")
                return

            # 获取应用详情
            await steam_service.fetch_app_details(app_id_str)

            # 获取文件列表
            files = await repo_manager.fetch_repository_files(repo, app_id_str)
            if not files:
                logger.error("❌ 无法获取仓库文件")
                return

            # 并发处理所有文件
            logger.info("⏳ 正在处理仓库文件...")
            success = await repo_manager.process_files(
                repo, app_id_str, files, steam_path
            )

            if not success:
                logger.warning("❗ 部分文件处理失败")

            # 保存配置
            save_success = await file_processor.save_lua_config(
                app_id_str,
                steam_service.app_name,
                steam_path,
                args.fixed,
            )

            if save_success:
                logger.info(f"✅ 操作完成！应用: {steam_service.app_name or app_id_str}")
            else:
                logger.error("❌ 保存配置失败")

            # 处理DLC
            if steam_service.dlc_ids:
                logger.info(f"🎯 检测到 {len(steam_service.dlc_ids)} 个DLC，正在处理...")

                # 为DLC复用资源
                dlc_processor = FileService()
                dlc_repo_manager = GitHubService(api_client, dlc_processor)

                for dlc_id in steam_service.dlc_ids:
                    dlc_id_str = str(dlc_id)
                    dlc_repo = await dlc_repo_manager.find_repository(dlc_id_str, custom_repos)

                    if dlc_repo:
                        dlc_files = await dlc_repo_manager.fetch_repository_files(dlc_repo, dlc_id_str)
                        if dlc_files:
                            # 清理之前的状态
                            dlc_processor.clear()

                            # 处理DLC文件（下载清单等）
                            await dlc_repo_manager.process_files(
                                dlc_repo, dlc_id_str, dlc_files, steam_path
                            )

                            # 保存DLC配置
                            await dlc_processor.save_lua_config(
                                dlc_id_str,
                                None,
                                steam_path,
                                args.fixed,
                            )
                            logger.info(f"✅ DLC {dlc_id_str} 处理完成")
                    else:
                        logger.warning(f"❗ 未找到 DLC {dlc_id_str} 的仓库")

        except KeyboardInterrupt:
            logger.warning("❗ 操作已被用户中断")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ 发生异常: {str(e)}")
            if args.debug:
                logger.exception("异常详情:")
            sys.exit(1)

    # 完成提示
    if not args.appid:
        try:
            Console().input("\n[dim]按回车键退出...[/dim]")
        except Exception:
            pass
