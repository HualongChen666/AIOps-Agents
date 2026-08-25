# -*- coding: utf-8 -*-
"""
Ansible Playbook Manager
Ansible Playbook执行管理器

功能:
- Playbook加载与解析
- 异步执行Playbook
- 执行结果收集
- 变量注入
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class PlaybookManager:
    """
    Ansible Playbook管理器

    管理Ansible Playbook的加载、执行和结果收集。

    参数:
        playbook_dir: Playbook目录
        inventory_file: Inventory文件路径
        dry_run: 是否只模拟执行
    """

    def __init__(
        self,
        playbook_dir: str = "playbooks",
        inventory_file: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.playbook_dir = Path(playbook_dir)
        self.inventory_file = inventory_file
        self.dry_run = dry_run

        self._playbooks: Dict[str, Dict[str, Any]] = {}

        # 确保目录存在
        self.playbook_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Playbook manager initialized: dir=%s, dry_run=%s", playbook_dir, dry_run)

    def load_playbook(self, name: str, content: Optional[str] = None) -> bool:
        """
        加载Playbook

        参数:
            name: Playbook名称
            content: Playbook内容（YAML字符串），如果为None则从文件加载

        返回:
            是否加载成功
        """
        playbook_path = self.playbook_dir / f"{name}.yml"

        if content is None:
            if not playbook_path.exists():
                logger.warning("Playbook file not found: %s", playbook_path)
                return False

            try:
                with open(playbook_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as exc:
                logger.error("Failed to read playbook file %s: %s", playbook_path, exc)
                return False

        try:
            playbook = yaml.safe_load(content)
            self._playbooks[name] = {
                "content": content,
                "parsed": playbook,
                "path": str(playbook_path),
                "loaded_at": datetime.now().isoformat(),
            }
            logger.info("Playbook loaded: %s", name)
            return True

        except yaml.YAMLError as e:
            logger.error("Failed to parse playbook %s: %s", name, e)
            return False

    def get_playbook(self, name: str) -> Optional[Dict[str, Any]]:
        """获取Playbook"""
        return self._playbooks.get(name)

    def list_playbooks(self) -> List[str]:
        """列出所有已加载的Playbook"""
        return list(self._playbooks.keys())

    async def execute_playbook(
        self,
        name: str,
        extra_vars: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行Playbook

        参数:
            name: Playbook名称
            extra_vars: 额外变量
            tags: 执行的标签
            limit: 限制执行的主机

        返回:
            执行结果
        """
        if name not in self._playbooks:
            return {
                "success": False,
                "error": f"Playbook not found: {name}",
            }

        playbook_info = self._playbooks[name]
        playbook_path = playbook_info["path"]

        # 构建ansible-playbook命令
        cmd = ["ansible-playbook", playbook_path]

        # 添加inventory
        if self.inventory_file:
            cmd.extend(["-i", self.inventory_file])

        # 添加额外变量
        if extra_vars:
            extra_vars_str = json.dumps(extra_vars)
            cmd.extend(["--extra-vars", extra_vars_str])

        # 添加标签
        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        # 添加限制
        if limit:
            cmd.extend(["--limit", limit])

        # 添加check模式（dry run）
        if self.dry_run:
            cmd.append("--check")

        logger.info("Executing playbook: %s with command: %s", name, " ".join(cmd))

        try:
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "executed_at": datetime.now().isoformat(),
            }

            if result["success"]:
                logger.info("Playbook %s executed successfully", name)
            else:
                logger.error("Playbook %s failed with code %d", name, process.returncode)

            return result

        except FileNotFoundError:
            logger.error("ansible-playbook not found")
            return {
                "success": False,
                "error": "ansible-playbook not found",
            }
        except Exception as e:
            logger.error("Error executing playbook %s: %s", name, e)
            return {
                "success": False,
                "error": str(e),
            }

    def create_playbook(
        self,
        name: str,
        tasks: List[Dict[str, Any]],
        hosts: str = "all",
        become: bool = False,
        vars: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        创建Playbook

        参数:
            name: Playbook名称
            tasks: 任务列表
            hosts: 目标主机
            become: 是否使用sudo
            vars: 变量

        返回:
            是否创建成功
        """
        playbook = {
            "name": f"Auto-heal: {name}",
            "hosts": hosts,
            "become": become,
            "vars": vars or {},
            "tasks": tasks,
        }

        content = yaml.dump([playbook], default_flow_style=False)
        return self.load_playbook(name, content=content)

    def get_builtin_playbooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取内置Playbook模板

        返回:
            Playbook模板字典
        """
        return {
            "restart_service": [
                {
                    "name": "Restart service",
                    "systemd": {
                        "name": "{{ service_name }}",
                        "state": "restarted",
                    },
                }
            ],
            "clear_cache": [
                {
                    "name": "Clear application cache",
                    "shell": "rm -rf {{ cache_path }}/*",
                }
            ],
            "rotate_logs": [
                {
                    "name": "Rotate log files",
                    "shell": "logrotate -f {{ logrotate_config }}",
                }
            ],
            "update_config": [
                {
                    "name": "Update configuration file",
                    "copy": {
                        "src": "{{ config_src }}",
                        "dest": "{{ config_dest }}",
                        "backup": True,
                    },
                },
                {
                    "name": "Restart service after config update",
                    "systemd": {
                        "name": "{{ service_name }}",
                        "state": "restarted",
                    },
                },
            ],
            "scale_up": [
                {
                    "name": "Scale up deployment",
                    "kubernetes.core.k8s_scale": {
                        "name": "{{ deployment_name }}",
                        "namespace": "{{ namespace }}",
                        "kind": "Deployment",
                        "replicas": "{{ replicas }}",
                    },
                }
            ],
        }

    def create_builtin_playbook(self, template_name: str, name: str) -> bool:
        """
        从模板创建Playbook

        参数:
            template_name: 模板名称
            name: Playbook名称

        返回:
            是否创建成功
        """
        templates = self.get_builtin_playbooks()

        if template_name not in templates:
            logger.warning("Template not found: %s", template_name)
            return False

        tasks = templates[template_name]
        return self.create_playbook(name, tasks)

    def save_playbook(self, name: str) -> bool:
        """
        保存Playbook到文件

        参数:
            name: Playbook名称

        返回:
            是否保存成功
        """
        if name not in self._playbooks:
            logger.warning("Playbook not loaded: %s", name)
            return False

        playbook_info = self._playbooks[name]
        playbook_path = self.playbook_dir / f"{name}.yml"

        try:
            with open(playbook_path, "w", encoding="utf-8") as f:
                f.write(playbook_info["content"])
            logger.info("Playbook saved: %s", name)
            return True
        except Exception as e:
            logger.error("Failed to save playbook %s: %s", name, e)
            return False

    def delete_playbook(self, name: str) -> bool:
        """
        删除Playbook

        参数:
            name: Playbook名称

        返回:
            是否删除成功
        """
        if name in self._playbooks:
            del self._playbooks[name]

        playbook_path = self.playbook_dir / f"{name}.yml"
        if playbook_path.exists():
            playbook_path.unlink()
            logger.info("Playbook deleted: %s", name)
            return True

        return False


class PlaybookExecutor:
    """
    Playbook执行器

    负责协调Playbook的执行和结果处理。

    参数:
        playbook_manager: Playbook管理器
    """

    def __init__(self, playbook_manager: PlaybookManager):
        self.playbook_manager = playbook_manager
        self._executions: Dict[str, Dict[str, Any]] = {}

    async def execute_heal_playbook(
        self,
        heal_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行修复Playbook

        参数:
            heal_type: 修复类型
            params: 参数

        返回:
            执行结果
        """
        # 根据修复类型选择Playbook
        playbook_name = self._select_playbook(heal_type)

        if not playbook_name:
            return {
                "success": False,
                "error": f"No playbook found for heal type: {heal_type}",
            }

        # 确保Playbook已加载
        if playbook_name not in self.playbook_manager.list_playbooks():
            # 尝试从模板创建
            template_name = self._get_template_for_heal_type(heal_type)
            if template_name:
                self.playbook_manager.create_builtin_playbook(template_name, playbook_name)

        # 执行Playbook
        execution_id = f"{playbook_name}_{datetime.now().timestamp()}"

        self._executions[execution_id] = {
            "execution_id": execution_id,
            "playbook_name": playbook_name,
            "heal_type": heal_type,
            "params": params,
            "started_at": datetime.now().isoformat(),
            "status": "running",
        }

        result = await self.playbook_manager.execute_playbook(
            playbook_name,
            extra_vars=params,
        )

        self._executions[execution_id].update(
            {
                "result": result,
                "completed_at": datetime.now().isoformat(),
                "status": "completed" if result["success"] else "failed",
            }
        )

        return result

    def _select_playbook(self, heal_type: str) -> Optional[str]:
        """根据修复类型选择Playbook"""
        playbook_map = {
            "restart_service": "restart_service",
            "clear_cache": "clear_cache",
            "rotate_logs": "rotate_logs",
            "update_config": "update_config",
            "scale_up": "scale_up",
        }
        return playbook_map.get(heal_type)

    def _get_template_for_heal_type(self, heal_type: str) -> Optional[str]:
        """获取修复类型对应的模板"""
        return self._select_playbook(heal_type)

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行记录"""
        return self._executions.get(execution_id)

    def get_executions(self) -> List[Dict[str, Any]]:
        """获取所有执行记录"""
        return list(self._executions.values())
