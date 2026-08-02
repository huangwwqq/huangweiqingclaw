"""
AI部门
一个部门 = 一个主管(leader_claw) + 若干岗位(每个岗位 = 技能目录 + 职责提示词 + 编制人数)
换部门只需要换一份岗位配置,不需要改代码
"""
import sys
sys.path.append('../')
from claw import *
from concurrent.futures import ThreadPoolExecutor


class AIDepartment:
    """
    通用AI部门多智能体协同调度器

    调度模型:任务串行、单任务内分片并行
    - 主管把用户诉求拆成有序的子任务,逐个下发
    - 同一个子任务会先切成互不重叠的分片再并发:有明确数量的按总量平分(5篇2人=3篇+2篇),
      能按维度并行的按维度分,不可拆的只派一个人,避免多人各做一遍全量
    - 各分片产出由主管合并成一份并验收,不通过则带整改意见重试,重试仍不过由主管亲自兜底做全量
    """

    def __init__(
        self,
        leader_claw: HuangwqClaw,
        employee_claw_list: List[HuangwqClaw] = None,
        staff_list: List[dict] = None,
        department_name: str = '通用AI部门',
        department_goal: str = '',
        work_number: int = department_work_number,
        max_workers: int = department_max_workers,
        max_retry: int = department_max_retry,

    ):
        """
        :param leader_claw: 主管智能体,负责拆解、验收、兜底、汇总
        :param employee_claw_list: 员工智能体列表(兼容入口),会自动按 skill_folders 生成岗位元数据
        :param staff_list: 带岗位元数据的员工列表,由 from_config 生成,元素结构:
                           {'role_name','duty','skill_folders','worker_id','claw'}
        :param department_name: 部门名称
        :param department_goal: 部门长期目标,会注入主管与员工的上下文
        :param work_number: 单次协同最多执行的任务步数,防止验收重试导致死循环
        :param max_workers: 单个任务最多并发的员工数
        :param max_retry: 单个任务验收不通过后的最大重试次数
        """
        self.leader_claw = leader_claw
        self.department_name = department_name
        self.department_goal = department_goal
        self.work_number = work_number
        self.max_workers = max(1, max_workers)
        self.max_retry = max(0, max_retry)

        if staff_list:
            self.staff_list = staff_list
        else:
            self.staff_list = self._build_default_staff(employee_claw_list or [])
        self.employee_claw_list = [item['claw'] for item in self.staff_list]

    @staticmethod
    def _build_default_staff(employee_claw_list: List[HuangwqClaw]) -> List[dict]:
        """直接传入 claw 实例时,按实例自带的技能反推一份岗位元数据兜底"""
        staff_list = []
        for index, employee_claw in enumerate(employee_claw_list, start=1):
            skill_folders = getattr(employee_claw, 'skill_folders', None) or []
            role_name = f'员工{index}'
            staff_list.append({
                'role_name': role_name,
                'duty': '通用执行岗位,按主管分配的任务执行',
                'skill_folders': skill_folders,
                'worker_id': f'{role_name}-1',
                'claw': employee_claw,
            })
        return staff_list

    @staticmethod
    def _get_model_config(
        member_config: DepartmentMemberConfig,
    ) -> dict:
        """返回主管或岗位自身的模型配置。"""
        return {
            'model_manufacturer': member_config.model_manufacturer,
            'model_name': member_config.model_name,
            'base_url': member_config.base_url,
            'api_key': member_config.api_key,
            'temperature': member_config.temperature
                           if member_config.temperature is not None else 0.7,
        }

    @classmethod
    def from_config(
        cls,
        leader_config: dict = None,
        member_config_list: List[dict] = None,
        department_name: str = '通用AI部门',
        department_goal: str = '',
    ):
        """
        按部门配置批量创建主管与员工

        :param leader_config: 主管配置，包含其自身模型配置
        :param member_config_list: 岗位配置列表，每个岗位包含其自身模型配置
        :param department_name: 部门名称
        :param department_goal: 部门长期目标
        """
        if not member_config_list:
            raise ValueError('缺少岗位配置 member_config_list,部门至少要有一个岗位')

        leader_config = leader_config or {}
        leader_member_config = DepartmentMemberConfig(**leader_config)
        leader_system_prompt = department_leader_prompt.format(
            department_name=department_name,
            department_goal=department_goal or '无明确长期目标,以完成用户当前诉求为准'
        )
        if leader_member_config.system_prompt:
            leader_system_prompt = f'{leader_system_prompt}\n{leader_member_config.system_prompt}'
        leader_claw = HuangwqClaw(
            system_prompt=leader_system_prompt,
            skill_folders=leader_member_config.skill_folders,
            **cls._get_model_config(leader_member_config)
        )

        staff_list = []
        for member_config_data in member_config_list:
            member_config = DepartmentMemberConfig(**member_config_data)
            if not member_config.role_name:
                logger.warning(f'岗位配置缺少 role_name,已跳过:{member_config_data}')
                continue

            skill_folders = member_config.skill_folders or []
            skill_desc = '、'.join(skill_folders) if skill_folders else '无专项技能,使用通用工具'
            for seq in range(1, max(1, member_config.headcount) + 1):
                worker_id = f'{member_config.role_name}-{seq}'
                employee_system_prompt = department_employee_prompt.format(
                    department_name=department_name,
                    role_name=member_config.role_name,
                    worker_id=worker_id,
                    duty=member_config.duty or '按主管分配的任务执行',
                    skill_desc=skill_desc
                )
                if member_config.system_prompt:
                    employee_system_prompt = f'{employee_system_prompt}\n{member_config.system_prompt}'

                employee_claw = HuangwqClaw(
                    system_prompt=employee_system_prompt,
                    skill_folders=member_config.skill_folders,
                    **cls._get_model_config(member_config)
                )
                staff_list.append({
                    'role_name': member_config.role_name,
                    'duty': member_config.duty,
                    'skill_folders': skill_folders,
                    'worker_id': worker_id,
                    'claw': employee_claw,
                })
                logger.info(f'部门 {department_name} 已入职:{worker_id},技能:{skill_desc}')

        if not staff_list:
            raise ValueError('岗位配置全部无效,部门没有可用员工')

        cls._share_db_object(leader_claw, staff_list)
        return cls(
            leader_claw=leader_claw,
            staff_list=staff_list,
            department_name=department_name,
            department_goal=department_goal,
        )

    @staticmethod
    def _share_db_object(leader_claw: HuangwqClaw, staff_list: List[dict]):
        """
        每个 HuangwqClaw 实例都会各自建两个 MySQL 连接池(mincached=5),
        员工多了会把连接数撑爆,这里统一复用主管那一份,并关掉多余的池
        """
        for item in staff_list:
            employee_claw = item['claw']
            for attr_name in ('tb_self_awareness_object', 'tb_agent_message_object'):
                shared_object = getattr(leader_claw, attr_name, None)
                own_object = getattr(employee_claw, attr_name, None)
                if shared_object is None or own_object is shared_object:
                    continue
                try:
                    own_object.db.close()
                except Exception as e:
                    logger.warning(f"{item['worker_id']} 释放多余连接池失败:{e}")
                setattr(employee_claw, attr_name, shared_object)

    def _build_roster_prompt(self) -> str:
        """生成员工花名册,让主管知道任务能派给谁"""
        role_map = dict()
        for item in self.staff_list:
            role_name = item['role_name']
            if role_name not in role_map:
                role_map[role_name] = {
                    'duty': item.get('duty') or '按主管分配的任务执行',
                    'skill_folders': list(item.get('skill_folders') or []),
                    'count': 0,
                }
            role_map[role_name]['count'] += 1

        lines = [f'「{self.department_name}」在岗人员花名册:']
        for role_name, info in role_map.items():
            skill_desc = '、'.join(info['skill_folders']) if info['skill_folders'] else '无专项技能,使用通用工具'
            lines.append(
                f"- 岗位:{role_name} | 在岗人数:{info['count']} | 职责:{info['duty']} | 技能:{skill_desc}"
            )
        return '\n'.join(lines)

    def _role_headcount(self, role_name: str) -> int:
        return len([item for item in self.staff_list if item['role_name'] == role_name]) or 1

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        """模型返回的数字可能是字符串、小数甚至中文,统一兜底"""
        if isinstance(value, bool) or value is None:
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        matched = re.search(r'\d+', str(value))
        return int(matched.group()) if matched else default

    @staticmethod
    def _clamp_parallel_count(task: DepartmentTask) -> int:
        """并发人数不能超过这个任务实际能拆出来的份数,否则会有人重复劳动"""
        if task.split_mode == 'quantity':
            if task.workload_total <= 0:
                return 1
            return max(1, min(task.parallel_count, task.workload_total))
        if task.split_mode == 'dimension':
            if not task.split_items:
                return 1
            return max(1, min(task.parallel_count, len(task.split_items)))
        return 1

    @staticmethod
    def _split_workload(total: int, worker_count: int) -> List[int]:
        """把总量尽量平均地切给每个人,余数从前往后分:5个2人 -> [3,2],7个3人 -> [3,2,2]"""
        if total <= 0 or worker_count <= 0:
            return []
        worker_count = min(worker_count, total)
        base, remainder = divmod(total, worker_count)
        return [base + 1 if index < remainder else base for index in range(worker_count)]

    def _build_shards(self, task: DepartmentTask, workers: List[dict]) -> List[dict]:
        """
        把一个任务切成互不重叠的分片,一片对应一个人
        - quantity:按总量平分,并给出每片负责的排序区间
        - dimension:按主管给的维度清单分,人多于维度数时裁掉多余的人
        - none:不可拆,只留一个人做,避免多人重复做全量
        """
        if not workers:
            return []

        unit = task.workload_unit or '份'
        if task.split_mode == 'quantity' and task.workload_total > 0:
            share_list = self._split_workload(task.workload_total, len(workers))
            shards, start = [], 1
            for index, share in enumerate(share_list):
                end = start + share - 1
                shards.append({
                    'worker': workers[index],
                    'shard_index': index + 1,
                    'shard_count': len(share_list),
                    'shard_desc': f'第{index + 1}片:{share}{unit}(整体排序第{start}到第{end})',
                    'shard_prompt': (
                        f'本任务总量为 {task.workload_total}{unit},由 {len(share_list)} 人分片并行完成,'
                        f'你是第 {index + 1} 片。\n'
                        f'你只负责其中 {share}{unit},对应整体排序的第 {start} 到第 {end} 个,'
                        f'既不要多做也不要少做。\n'
                        f'请和同事使用同一套排序规则(如按点赞量从高到低)后再取你负责的区间,'
                        f'保证各分片之间不重复、不遗漏,其余部分同事正在并行处理。\n'
                        f'交付时请注明你实际完成的数量和所属区间。'
                    ),
                })
                start = end + 1
            return shards

        if task.split_mode == 'dimension' and task.split_items:
            worker_count = min(len(workers), len(task.split_items))
            bucket_list = [[] for _ in range(worker_count)]
            for index, item in enumerate(task.split_items):
                bucket_list[index % worker_count].append(item)
            shards = []
            for index, bucket in enumerate(bucket_list):
                bucket_desc = '、'.join(bucket)
                shards.append({
                    'worker': workers[index],
                    'shard_index': index + 1,
                    'shard_count': worker_count,
                    'shard_desc': f'第{index + 1}片:{bucket_desc}',
                    'shard_prompt': (
                        f'本任务按维度拆分给 {worker_count} 人并行完成,你是第 {index + 1} 片。\n'
                        f'你只负责这部分:{bucket_desc}\n'
                        f'其余维度由同事并行处理,不要越界去做,否则就是重复劳动。'
                    ),
                })
            return shards

        if len(workers) > 1:
            logger.info(f"任务 {task.task_id} 不可拆分,只派给 {workers[0]['worker_id']} 单人执行,避免多人重复做全量")
        return [{
            'worker': workers[0],
            'shard_index': 1,
            'shard_count': 1,
            'shard_desc': '',
            'shard_prompt': '',
        }]

    def _plan_tasks(self, user_input: str, file_url_path_list: list = None) -> List[DepartmentTask]:
        """主管拆解任务,输出有序的子任务列表"""
        role_names = []
        for item in self.staff_list:
            if item['role_name'] not in role_names:
                role_names.append(item['role_name'])

        system_prompt = (
            f'{task_assignment_prompt}\n'
            f'{self._build_roster_prompt()}\n'
            f'部门目标:{self.department_goal or "以完成用户当前诉求为准"}\n\n'
            '分配规则:\n'
            f'1. assignee_roles 只能从这些岗位名中选择,不得虚构岗位:{role_names}\n'
            '2. task_list 按执行先后顺序排列,后面的任务可以使用前面任务的产出\n'
            '3. 同一个任务可以派给多名同岗位员工并行执行,用 parallel_count 指定人数,不得超过该岗位在岗人数\n'
            '4. 任务数量控制在 1-8 个,一步能做完就不要硬拆\n'
            '5. acceptance_criteria 必须可验收,不要写"做好为止"这种空话\n'
            '6. 多人并行必须说明活怎么分,否则每个人都做一遍全量就是重复劳动,按下面三种方式之一填写:\n'
            '   - 有明确数量的任务(如"采集5篇笔记"):split_mode 填 quantity,workload_total 填总数(5),'
            'workload_unit 填单位(篇笔记),系统会自动把总量平分给多人(5篇2人就是3篇+2篇)\n'
            '   - 没有数量但能按维度并行的任务(如按不同关键词、不同平台分别采集):split_mode 填 dimension,'
            'split_items 填每一份的具体内容,有几份就最多派几个人\n'
            '   - 不可拆的任务(如写一篇稿子、做一次汇总分析):split_mode 填 none,parallel_count 必须为 1\n'
            '7. workload_total 只填这一个子任务自己的量,不要把整个项目的量填进来\n\n'
            '严格只输出如下JSON,不要输出任何解释、markdown标记或多余文字:\n'
            '{"task_list":[{"task_id":"T1","title":"任务标题","description":"任务详细描述",'
            '"assignee_roles":["岗位名"],"parallel_count":1,"workload_total":0,"workload_unit":"",'
            '"split_mode":"none","split_items":[],"acceptance_criteria":"验收标准",'
            '"expected_output":"期望交付物"}]}'
        )
        human_input = f'用户诉求:{user_input}'
        if file_url_path_list:
            human_input += f'\n附件列表:{file_url_path_list[:file_list_max_length]}'

        try:
            prompt = ChatPromptTemplate.from_messages([
                ('system', '{system_prompt}'),
                ('human', '{user_input}')
            ])
            chain = prompt | self.leader_claw.llm | JsonOutputParser()
            result = chain.invoke({'system_prompt': system_prompt, 'user_input': human_input})
        except Exception as e:
            logger.error(f'主管任务拆解失败,启用单任务兜底:{e}')
            return self._fallback_task_list(user_input)

        raw_task_list = result.get('task_list') if isinstance(result, dict) else result
        if not isinstance(raw_task_list, list) or not raw_task_list:
            logger.warning(f'主管任务拆解结果为空,启用单任务兜底,原始返回:{result}')
            return self._fallback_task_list(user_input)

        task_list = []
        for index, raw_task in enumerate(raw_task_list, start=1):
            if not isinstance(raw_task, dict):
                continue
            split_mode = str(raw_task.get('split_mode') or 'none').strip().lower()
            if split_mode not in ('quantity', 'dimension', 'none'):
                split_mode = 'none'
            task = DepartmentTask(
                task_id=str(raw_task.get('task_id') or f'T{index}'),
                title=str(raw_task.get('title') or f'子任务{index}'),
                description=str(raw_task.get('description') or raw_task.get('title') or user_input),
                assignee_roles=[str(role) for role in (raw_task.get('assignee_roles') or []) if str(role).strip()],
                parallel_count=self._safe_int(raw_task.get('parallel_count'), default=1),
                workload_total=self._safe_int(raw_task.get('workload_total'), default=0),
                workload_unit=str(raw_task.get('workload_unit') or ''),
                split_mode=split_mode,
                split_items=[str(item) for item in (raw_task.get('split_items') or []) if str(item).strip()],
                acceptance_criteria=str(raw_task.get('acceptance_criteria') or ''),
                expected_output=str(raw_task.get('expected_output') or ''),
            )
            if not task.assignee_roles:
                task.assignee_roles = role_names[:1]
            max_headcount = max(self._role_headcount(role) for role in task.assignee_roles)
            task.parallel_count = max(1, min(task.parallel_count, max_headcount, self.max_workers))
            task.parallel_count = self._clamp_parallel_count(task)
            task_list.append(task)

        if not task_list:
            return self._fallback_task_list(user_input)

        logger.info(f'主管拆解出 {len(task_list)} 个子任务:{[task.title for task in task_list]}')
        return task_list

    def _fallback_task_list(self, user_input: str) -> List[DepartmentTask]:
        """拆解失败兜底:整个诉求当成一个任务,派给所有岗位"""
        role_names = []
        for item in self.staff_list:
            if item['role_name'] not in role_names:
                role_names.append(item['role_name'])
        return [DepartmentTask(
            task_id='T1',
            title='完成用户诉求',
            description=user_input,
            assignee_roles=role_names,
            parallel_count=1,
            acceptance_criteria='完整回答用户诉求,数据与结论真实可验证',
            expected_output='可直接交付给用户的完整结果',
        )]

    def _pick_workers(self, task: DepartmentTask) -> List[dict]:
        """按任务指定的岗位挑人,同岗位可以挑多人并发"""
        selected = []
        for role_name in task.assignee_roles:
            matched = [item for item in self.staff_list if item['role_name'] == role_name]
            if not matched:
                lowered = (role_name or '').strip().lower()
                matched = [
                    item for item in self.staff_list
                    if lowered and (lowered in item['role_name'].lower() or item['role_name'].lower() in lowered)
                ]
            if not matched:
                logger.warning(f'任务 {task.task_id} 指定的岗位 {role_name} 不存在,已忽略')
                continue
            selected.extend(matched[:max(1, task.parallel_count)])

        if not selected:
            logger.warning(f'任务 {task.task_id} 未匹配到任何岗位,默认派给第一个员工')
            selected = self.staff_list[:1]

        workers, seen_worker_id = [], set()
        for item in selected:
            if item['worker_id'] in seen_worker_id:
                continue
            seen_worker_id.add(item['worker_id'])
            workers.append(item)
        return workers[:self.max_workers]

    def _build_worker_input(
        self,
        task: DepartmentTask,
        user_input: str,
        context_digest: str,
        shard: dict = None,
    ) -> str:
        """拼装派给员工的任务输入:部门背景 + 上游成果 + 当前任务 + 本人分片 + 整改意见"""
        sections = [
            f'所属部门:{self.department_name}',
            f'部门目标:{self.department_goal or "以完成用户当前诉求为准"}',
            f'用户原始诉求:{user_input}',
            f'上游已完成成果摘要:\n{context_digest}' if context_digest else '上游已完成成果摘要:无(你是第一步)',
            (
                f'--- 你本次要完成的子任务 ---\n'
                f'任务编号:{task.task_id}\n'
                f'任务标题:{task.title}\n'
                f'任务描述:{task.description}\n'
                f'验收标准:{task.acceptance_criteria or "完整达成任务描述"}\n'
                f'期望交付物:{task.expected_output or "结构化的执行结果"}'
            ),
        ]
        shard_prompt = (shard or {}).get('shard_prompt') or ''
        if shard_prompt:
            sections.append(f'--- 你的分工(只做这一份) ---\n{shard_prompt}')
        if task.extra_note:
            sections.append(f'主管上一轮的整改意见(必须逐条落实):\n{task.extra_note}')
        sections.append('请直接执行该任务并输出交付物,不要复述任务本身。')
        return '\n\n'.join(sections)

    @staticmethod
    def _extract_output(work_response: dict) -> str:
        """从 claw.work 的返回里提取员工交付物"""
        summary_message = (work_response.get('ai_summary_msg') or {}).get('message') or ''
        if summary_message.strip():
            return summary_message.strip()
        agent_message_list = [
            msg.get('message') or ''
            for msg in work_response.get('message_list') or []
            if msg.get('role') == 'agent' and msg.get('message')
        ]
        return '\n'.join(agent_message_list).strip()

    def _run_task_once(
        self,
        task: DepartmentTask,
        shard: dict,
        worker_input: str,
        user_id: str,
        message_id: str,
        file_url_path_list: list = None,
    ) -> TaskExecuteResult:
        """单个员工执行自己那一片任务,员工之间用子会话id隔离各自的记忆"""
        worker = shard['worker']
        result = TaskExecuteResult(
            task_id=task.task_id,
            role_name=worker['role_name'],
            worker_id=worker['worker_id'],
            shard_desc=shard.get('shard_desc') or '',
        )
        try:
            work_response = worker['claw'].work(
                user_id=user_id,
                user_input=worker_input,
                message_id=f"{message_id}-{worker['worker_id']}",
                file_url_path_list=file_url_path_list
            )
        except Exception as e:
            logger.error(f"{worker['worker_id']} 执行任务 {task.task_id} 抛出异常:{e}")
            result.error_code = 2
            result.error_msg = f'员工执行异常:{e}'
            return result

        if not isinstance(work_response, dict):
            result.error_code = 2
            result.error_msg = '员工返回结构异常'
            return result

        result.output = self._extract_output(work_response)
        work_error_code = work_response.get('error_code') or 0
        if work_error_code:
            result.error_code = work_error_code
            result.error_msg = work_response.get('error_msg') or '员工执行失败'
        elif not result.output:
            result.error_code = 2
            result.error_msg = '员工没有产出任何有效内容'
        return result

    def _run_task(
        self,
        task: DepartmentTask,
        shard_list: List[dict],
        user_id: str,
        user_input: str,
        context_digest: str,
        message_id: str,
        file_url_path_list: list = None,
    ) -> List[TaskExecuteResult]:
        """同岗位多人并行执行同一个任务的不同分片,每个人拿到的输入都带自己那一份的范围"""
        shard_input_list = [
            (shard, self._build_worker_input(task, user_input=user_input, context_digest=context_digest, shard=shard))
            for shard in shard_list
        ]
        if len(shard_input_list) == 1:
            shard, worker_input = shard_input_list[0]
            return [self._run_task_once(task, shard, worker_input, user_id, message_id, file_url_path_list)]

        logger.info(
            f'任务 {task.task_id} 拆成 {len(shard_list)} 片并行下发:'
            f"{[(item['worker']['worker_id'], item['shard_desc']) for item in shard_list]}"
        )
        result_list = []
        with ThreadPoolExecutor(max_workers=min(len(shard_input_list), self.max_workers)) as executor:
            future_list = [
                executor.submit(
                    self._run_task_once, task, shard, worker_input, user_id, message_id, file_url_path_list
                )
                for shard, worker_input in shard_input_list
            ]
            for (shard, _), future in zip(shard_input_list, future_list):
                worker = shard['worker']
                try:
                    result_list.append(future.result())
                except Exception as e:
                    logger.error(f"{worker['worker_id']} 并发执行任务 {task.task_id} 失败:{e}")
                    result_list.append(TaskExecuteResult(
                        task_id=task.task_id,
                        role_name=worker['role_name'],
                        worker_id=worker['worker_id'],
                        shard_desc=shard.get('shard_desc') or '',
                        error_code=2,
                        error_msg=f'并发执行异常:{e}'
                    ))
        return result_list

    @staticmethod
    def _workload_note(task: DepartmentTask) -> str:
        """给归并和验收环节说明这个任务的总量要求"""
        if task.split_mode == 'quantity' and task.workload_total > 0:
            return f'该任务按数量分片并行执行,汇总后的总量必须是 {task.workload_total}{task.workload_unit or "份"}'
        if task.split_mode == 'dimension' and task.split_items:
            return f'该任务按维度分片并行执行,需要覆盖的维度:{"、".join(task.split_items)}'
        return ''

    def _merge_outputs(self, task: DepartmentTask, result_list: List[TaskExecuteResult]) -> str:
        """把多名员工的分片交付物合并成一份"""
        success_list = [item for item in result_list if item.error_code == 0 and item.output]
        failed_list = [item for item in result_list if item.error_code != 0 or not item.output]
        failed_note = '\n'.join(
            f'【{item.worker_id} {item.shard_desc or "全量"} 执行失败】{item.error_msg}' for item in failed_list
        )

        if not success_list:
            return ''
        if len(success_list) == 1:
            single_output = success_list[0].output
            return f'{single_output}\n\n{failed_note}' if failed_note else single_output

        merge_input = '\n\n'.join(
            f'【{item.worker_id} {item.shard_desc or "全量"} 交付】\n{item.output}' for item in success_list
        )
        if failed_note:
            merge_input = f'{merge_input}\n\n{failed_note}'

        workload_note = self._workload_note(task)
        try:
            prompt = ChatPromptTemplate.from_messages([
                ('system', '{system_prompt}'),
                ('human', '{user_input}')
            ])
            chain = prompt | self.leader_claw.llm | StrOutputParser()
            merged = chain.invoke({
                'system_prompt': task_merge_prompt,
                'user_input': (
                    f'子任务:{task.title}\n'
                    f'任务描述:{task.description}\n'
                    f'{workload_note}\n\n'
                    f'各分片交付内容:\n{preliminary_compression(merge_input)}'
                )
            })
            if merged and merged.strip():
                return merged.strip()
        except Exception as e:
            logger.warning(f'任务 {task.task_id} 多员工产出归并失败,直接拼接:{e}')
        return merge_input

    def _review(self, task: DepartmentTask, merged_output: str) -> TaskReviewResult:
        """主管验收任务产出"""
        if not merged_output.strip():
            return TaskReviewResult(
                passed=False,
                reason='本任务没有任何有效交付物',
                suggestion='请重新执行任务,必须调用工具真实执行并给出可验证的交付物'
            )

        workload_note = self._workload_note(task)
        review_input = (
            f'子任务:{task.title}\n'
            f'任务描述:{task.description}\n'
            f'验收标准:{task.acceptance_criteria or "完整达成任务描述"}\n'
            f'期望交付物:{task.expected_output or "结构化的执行结果"}\n'
            f'{f"总量要求:{workload_note}" if workload_note else ""}\n\n'
            f'汇总后的交付内容:\n{preliminary_compression(merged_output)}'
        )
        try:
            prompt = ChatPromptTemplate.from_messages([
                ('system', '{system_prompt}'),
                ('human', '{user_input}')
            ])
            chain = prompt | self.leader_claw.llm | JsonOutputParser()
            result = chain.invoke({'system_prompt': task_review_prompt, 'user_input': review_input})
        except Exception as e:
            logger.warning(f'任务 {task.task_id} 验收结果解析失败,默认放行:{e}')
            return TaskReviewResult(passed=True, reason=f'验收结果解析失败,默认放行:{e}')

        if not isinstance(result, dict):
            return TaskReviewResult(passed=True, reason='验收返回结构异常,默认放行')

        passed = result.get('passed')
        if isinstance(passed, str):
            passed = passed.strip().lower() in ('true', '1', 'yes', '是', '通过')
        return TaskReviewResult(
            passed=bool(passed),
            reason=str(result.get('reason') or ''),
            suggestion=str(result.get('suggestion') or '')
        )

    def _leader_fallback(
        self,
        task: DepartmentTask,
        worker_input: str,
        review: TaskReviewResult,
        user_id: str,
        message_id: str,
        file_url_path_list: list = None,
    ) -> TaskExecuteResult:
        """员工反复交付不合格时,主管亲自兜底执行"""
        logger.warning(f'任务 {task.task_id} 员工交付不合格,主管开始兜底,原因:{review.reason}')
        fallback_input = (
            f'{worker_input}\n\n'
            f'--- 兜底说明 ---\n'
            f'该任务下属已执行 {task.retry_count + 1} 次仍未通过验收,验收结论:{review.reason}\n'
            f'整改意见:{review.suggestion}\n'
            f'现在由你亲自执行该任务,直接给出合格的交付物。'
        )
        workload_note = self._workload_note(task)
        if workload_note:
            fallback_input += f'\n{workload_note},这次由你独立完成全量,不再分片。'
        result = TaskExecuteResult(
            task_id=task.task_id, role_name='部门主管', worker_id='leader', shard_desc='全量兜底'
        )
        try:
            work_response = self.leader_claw.work(
                user_id=user_id,
                user_input=fallback_input,
                message_id=f'{message_id}-leader',
                file_url_path_list=file_url_path_list
            )
        except Exception as e:
            logger.error(f'任务 {task.task_id} 主管兜底异常:{e}')
            result.error_code = 2
            result.error_msg = f'主管兜底异常:{e}'
            return result

        result.output = self._extract_output(work_response)
        work_error_code = work_response.get('error_code') or 0
        if work_error_code:
            result.error_code = work_error_code
            result.error_msg = work_response.get('error_msg') or '主管兜底失败'
        elif not result.output:
            result.error_code = 2
            result.error_msg = '主管兜底没有产出任何有效内容'
        return result

    def _append_digest(self, context_digest: str, task: DepartmentTask, output: str) -> str:
        """把已完成任务的成果沉淀成跨任务上下文,过长时交给主管压缩"""
        digest = f'{context_digest}\n\n--- 任务 {task.task_id} {task.title} 成果 ---\n{output}'.strip()
        if len(digest) > department_digest_limit:
            logger.info(f'部门上下文摘要过长({len(digest)} 字符),执行压缩')
            try:
                digest = self.leader_claw._compress_text(digest)
            except Exception as e:
                logger.warning(f'部门上下文压缩失败,退化为首尾截断:{e}')
                keep_len = department_digest_limit // 2
                digest = f'{digest[:keep_len]}\n\n[...中间内容已截断...]\n\n{digest[-keep_len:]}'
        return digest

    def _final_summary(self, user_input: str, context_digest: str, task_record_list: list) -> str:
        """主管把所有任务成果汇总成最终交付"""
        if not context_digest.strip():
            return '本次协同没有产生任何有效成果,请检查任务描述或员工技能配置。'

        unfinished_note = '\n'.join(
            f"任务 {record['task_id']} {record['title']} 未通过验收:{record['review_reason']}"
            for record in task_record_list if not record.get('passed')
        )
        summary_input = (
            f'用户原始诉求:{user_input}\n\n'
            f'各子任务成果:\n{context_digest}'
        )
        if unfinished_note:
            summary_input += f'\n\n未完成或未通过验收的任务:\n{unfinished_note}'

        try:
            prompt = ChatPromptTemplate.from_messages([
                ('system', '{system_prompt}'),
                ('human', '{user_input}')
            ])
            chain = prompt | self.leader_claw.llm | StrOutputParser()
            final_answer = chain.invoke({
                'system_prompt': department_summary_prompt,
                'user_input': preliminary_compression(summary_input)
            })
            if final_answer and final_answer.strip():
                return final_answer.strip()
        except Exception as e:
            logger.warning(f'部门最终汇总失败,直接返回成果摘要:{e}')
        return context_digest

    def execute_task(
        self,
        user_id: str,  # 用户id
        user_input: str,  # 用户输入
        message_id: str = '',  # 对话id(记忆)
        file_url_path_list: list = None,  # 文件url列表
    ):
        """
        执行任务逻辑
        1. 用户传入任务
        2. 先由主管(self.leader_claw)分配任务
        while 循环(当work_number为0 或者 任务完成,方可跳出)
            work_number -= 1
            同一个任务可由多名同岗位员工并行执行,产出合并后交给主管判断当前任务是否完成
            未完成则带整改意见重试,重试仍不过由主管兜底,主管兜底也失败则直接跳出
            下一个任务
        3. 主管汇总所有成果,输出最终交付
        """
        if not user_id:
            logger.warning('缺少用户id')
            return DepartmentResponse(
                department_name=self.department_name, error_code=1, error_msg='缺少用户id'
            ).__dict__
        if not user_input:
            logger.warning('缺少用户输入')
            return DepartmentResponse(
                user_id=user_id, department_name=self.department_name, error_code=1, error_msg='缺少用户输入'
            ).__dict__
        if not self.leader_claw:
            return DepartmentResponse(
                user_id=user_id, department_name=self.department_name, error_code=1, error_msg='部门缺少主管智能体'
            ).__dict__
        if not self.staff_list:
            return DepartmentResponse(
                user_id=user_id, department_name=self.department_name, error_code=1, error_msg='部门没有在岗员工'
            ).__dict__
        if not message_id:
            message_id = str(uuid.uuid4())
            logger.info(f'生成新部门协同会话,会话id:{message_id}')

        task_list = self._plan_tasks(user_input=user_input, file_url_path_list=file_url_path_list)
        if not task_list:
            return DepartmentResponse(
                user_id=user_id,
                message_id=message_id,
                department_name=self.department_name,
                error_code=2,
                error_msg='主管未能拆解出任何可执行任务'
            ).__dict__

        planned_task_list = [task.__dict__ for task in task_list]
        task_queue = list(task_list)
        task_record_list, context_digest = list(), ''
        work_number = self.work_number
        error_code, error_msg = 0, ''

        while task_queue and work_number > 0:
            work_number -= 1
            task = task_queue.pop(0)
            workers = self._pick_workers(task)
            shard_list = self._build_shards(task, workers)
            logger.info(
                f'开始执行任务 {task.task_id} {task.title},分工:'
                f"{[(item['worker']['worker_id'], item['shard_desc'] or '全量') for item in shard_list]}"
            )

            result_list = self._run_task(
                task=task,
                shard_list=shard_list,
                user_id=user_id,
                user_input=user_input,
                context_digest=context_digest,
                message_id=message_id,
                file_url_path_list=file_url_path_list
            )
            merged_output = self._merge_outputs(task, result_list)
            review = self._review(task, merged_output)
            record = {
                'task_id': task.task_id,
                'title': task.title,
                'assignee_roles': task.assignee_roles,
                'split_mode': task.split_mode,
                'workload_total': task.workload_total,
                'shard_list': [
                    {'worker_id': item['worker']['worker_id'], 'shard_desc': item['shard_desc'] or '全量'}
                    for item in shard_list
                ],
                'worker_id_list': [item['worker']['worker_id'] for item in shard_list],
                'retry_count': task.retry_count,
                'output': merged_output,
                'passed': review.passed,
                'review_reason': review.reason,
                'review_suggestion': review.suggestion,
                'leader_fallback': False,
            }

            if not review.passed:
                if task.retry_count < self.max_retry and work_number > 0:
                    task.retry_count += 1
                    task.extra_note = review.suggestion or review.reason
                    task_record_list.append(record)
                    task_queue.insert(0, task)
                    logger.warning(f'任务 {task.task_id} 验收不通过,第 {task.retry_count} 次重试,原因:{review.reason}')
                    continue

                fallback_result = self._leader_fallback(
                    task=task,
                    # 兜底由主管一个人做全量,不带分片
                    worker_input=self._build_worker_input(task, user_input=user_input, context_digest=context_digest),
                    review=review,
                    user_id=user_id,
                    message_id=message_id,
                    file_url_path_list=file_url_path_list
                )
                record['leader_fallback'] = True
                if fallback_result.error_code or not fallback_result.output:
                    record['review_reason'] = f'{review.reason};主管兜底失败:{fallback_result.error_msg}'
                    task_record_list.append(record)
                    error_code = 3
                    error_msg = f'任务 {task.task_id} {task.title} 员工与主管均执行失败:{fallback_result.error_msg}'
                    logger.error(error_msg)
                    break
                merged_output = fallback_result.output
                record['output'] = merged_output
                record['passed'] = True
                record['review_reason'] = f'{review.reason};已由主管兜底完成'

            task_record_list.append(record)
            context_digest = self._append_digest(context_digest, task, merged_output)

        if task_queue and error_code == 0:
            error_code = 4
            error_msg = f'达到最大任务步数 {self.work_number},仍有 {len(task_queue)} 个任务未执行'
            logger.warning(error_msg)

        final_answer = self._final_summary(
            user_input=user_input,
            context_digest=context_digest,
            task_record_list=task_record_list
        )
        return DepartmentResponse(
            user_id=user_id,
            message_id=message_id,
            department_name=self.department_name,
            task_list=planned_task_list,
            task_record_list=task_record_list,
            final_answer=final_answer,
            error_code=error_code,
            error_msg=error_msg
        ).__dict__


if __name__ == '__main__':
    # 换部门 = 换下面这份配置,代码不用动
    department = AIDepartment.from_config(
        leader_config={
            'skill_folders': ['xhs-apis'],
            'model_manufacturer': 'deepseek',
            'model_name': 'deepseek-v4-flash',
            'base_url': 'https://api.deepseek.com',
            'api_key': '***',
            'temperature': 0.7,
        },
        member_config_list=[
            {
                'role_name': '内容采集专员',
                'duty': '按关键词采集小红书笔记原始数据,包含作者、点赞、收藏、评论与标签',
                'skill_folders': ['xhs-apis'],
                'model_manufacturer': 'deepseek',
                'model_name': 'deepseek-v4-flash',
                'base_url': 'https://api.deepseek.com',
                'api_key': '***',
                'temperature': 0.7,
                'headcount': 2,  # 采5篇会自动切成3篇+2篇两片并发,不会两个人各采5篇
            },
            {
                'role_name': '数据分析师',
                'duty': '对采集到的原始数据做去重、清洗与指标分析,输出结构化洞察',
                'model_manufacturer': 'deepseek',
                'model_name': 'deepseek-v4-flash',
                'base_url': 'https://api.deepseek.com',
                'api_key': '***',
                'temperature': 0.7,
                'headcount': 1,
            },
            {
                'role_name': '文案策划',
                'duty': '基于数据洞察产出可直接发布的文案初稿',
                'model_manufacturer': 'deepseek',
                'model_name': 'deepseek-v4-flash',
                'base_url': 'https://api.deepseek.com',
                'api_key': '***',
                'temperature': 0.7,
                'headcount': 1,
            },
        ],
        department_name='内容运营部',
        department_goal='围绕指定选题完成素材采集、数据分析与成稿输出',
    )
    print(
        department.execute_task(
            user_id='huangweiqing',
            user_input=''
        )
    )
