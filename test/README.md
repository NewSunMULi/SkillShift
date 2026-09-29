# 火星探测器技能可靠性基准 / Mars rover skill-reliability benchmark

该包实现 `docs/plan.md` 的前两节和实验 0，仅依赖 Python 标准库。
It implements sections 1–2 of `docs/plan.md` and experiment 0 using only the Python standard library.

## 模块结构 / Architecture

- `environment/`：外部火星环境、语义标签和阶段调度。
  External Mars conditions, semantic tags, and phase scheduling.
- `rover/execution.py`：只校验并执行明确指定的技能。
  Validate and execute explicitly selected skills only.
- `rover/operators/`：完全独立于 LLM 的人工与自定义脚本操作入口。
  Manual and custom-script entry points that are independent of LLMs.
- `rover/agent.py`：自动可靠性系统接管探测器的编排入口。
  Orchestration entry point for autonomous reliability-system takeover.
- `rover/reliability/`：LLM 接口与非模型可靠性系统。
  LLM adapters and non-model reliability systems.
- `benchmark/`：在线系统不可见的概率真值。
  Probability truth hidden from online systems.
- `evaluation/`：实验共用的冻结日志、Dify 接入、输出契约、参考系统和评价指标。
  Shared frozen streams, Dify integration, contracts, reference systems, and metrics.
- `experiments/`：只包含实验 0、1、2 及联合运行入口的薄编排层。
  Thin orchestration for experiments 0, 1, 2, and their combined runner.
- `common/`：跨实验复用的报告输出等通用工具。
  Reporting and other utilities shared across experiments.

旧的 `mars_simulator.py`、`systems.py`、根目录实验入口和交互演示脚本已经移除；所有代码直接从所属
模块导入，避免兼容层掩盖依赖关系。

## 技能执行与三种操作方式 / Skill execution and three operation modes

`SkillExecutor` 是唯一执行入口，但不选择技能，也不知道技能来源。人工、脚本和自动智能体
分别位于不同模块中；只有 `LLMJsonAdapter` 会调用 LLM。
`SkillExecutor` is the only execution entry point, but it neither selects skills nor knows their
source. Manual, scripted, and autonomous modes live in separate modules; only `LLMJsonAdapter`
calls an LLM.

自定义脚本示例 / Custom script example:

```python
from test.rover.execution import SkillExecutor
from test.rover.operators import ScriptedOperator
from test.rover.simulator import MarsReliabilitySimulator

simulator = MarsReliabilitySimulator()
executor = SkillExecutor(simulator)

def strategy(context, logs, available_skills):
    return "heat" if "cold" in context.env_tags else "move"

operator = ScriptedOperator(executor, strategy)
result = operator.run_step(time=0, phase=1, context=simulator.contexts[0])
```

人工终端控制 / Manual terminal control:

```python
from test.rover.operators import ManualOperator

operator = ManualOperator(executor)
result = operator.run_step(time=0, phase=1, context=simulator.contexts[0])
```

LLM 自动接管 / LLM autonomous takeover:

```python
from test.rover.agent import AutonomousRoverAgent
from test.rover.reliability import LLMJsonAdapter

def call_model(system_prompt, user_prompt):
    # 此函数是唯一需要接入模型 SDK/API 的位置。
    # This is the only function that needs a model SDK/API.
    return model_client.complete(system_prompt, user_prompt)

llm_system = LLMJsonAdapter(model="your-model", complete=call_model)
agent = AutonomousRoverAgent(executor, llm_system)
agent_result = agent.run_step(
    time=0, phase=1, context=simulator.contexts[0], logs=[]
)
```

`AgentStepResult.decision` 完整保留报警、变化技能、变化上下文、概率估计、主动探测标志
和所选技能，`AgentStepResult.execution` 保存技能执行与状态转移结果。因此自动接管不会删减
可靠性评测信息。
`AgentStepResult.decision` preserves alarms, changed skills and contexts, probability estimates,
the probe flag, and the selected skill. `AgentStepResult.execution` stores execution and state
transition results, so autonomous takeover does not discard evaluation data.

## 运行 / Running

```bash
python -m test.experiments.experiment0
python -m test.experiments.run_1_2 --system id-baseline
python -m test.experiments.run_1_2 --system oracle
python -m unittest discover -s test -t . -v
```

## 实验 1–2 与 Dify Workflow / Experiments 1–2 and Dify Workflow

实验 1–2 使用冻结、按技能平衡的日志流。`id-baseline` 是不读取环境语义的统计基线，
`oracle` 只用于检查评测器上界，不能作为在线方法。真实 LLM 通过 Dify Workflow 接入：

```bash
export DIFY_API_KEY='app-...'
export DIFY_BASE_URL='http://localhost/v1'  # 或你的 Dify 服务 / or your Dify service
export DIFY_WORKFLOW_USER='deerlinkai-experiment'
export DIFY_MODEL_LABEL='provider/model-and-revision'
export DIFY_INPUT_NAME='request_json'
export DIFY_OUTPUT_NAME='result'
python -m test.experiments.run_1_2 --system dify --memory-log-limit 2000
```

不要把密钥写入仓库。Dify Start 节点需要一个字符串输入（默认 `request_json`），End 节点需要
输出一个 JSON 对象或 JSON 字符串（默认 `result`）。Workflow 内部可以自由配置模型、知识库检索、
外部存储或其他记忆节点。Workflow API 调用本身不应被假定为自动保留跨调用对话记忆；Python 会发送
全部历史的固定 100 条块级统计摘要、受限数量的近期原始日志以及上下文目录，并严格校验输出。
`DIFY_MODEL_LABEL` 仅用于结果溯源；真正的模型、温度、知识库版本和检索参数仍需在 Dify 中固定，
并随论文实验清单一起导出。每个被比较的 Workflow 应使用独立 API key 和明确版本，不能在实验期间
静默修改。

实验输出包含两个独立报警字典 `alarm_probability`、`alarm_applicability`，以及对所有 10 个技能的
`changed_contexts`、`failed_contexts`、`gained_contexts` ID 列表。任何未知 ID、缺失技能、额外字段
或非法 JSON 都会在该检查点按空预测计分，并记录到 `invalid_outputs`。

`ProbabilityOracle`、`MarsReliabilitySimulator.probability()` 和 `is_applicable()` 仅用于评估。
在线系统只能消费 `LogEntry`，不能获取阶段标签、变点或真实概率。
These probability APIs are evaluation-only. Online systems may consume `LogEntry` objects but
must not access phase labels, change points, or ground-truth probabilities.

30×10 标准网格覆盖全部命名环境和状态；额外 100 个泛化上下文使用确定性的双环境组合。
The 30-by-10 grid covers all named environments and states; 100 held-out contexts use deterministic
two-environment mixtures.
