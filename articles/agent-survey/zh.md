## Agent 系统概览

在一个 LLM 驱动的自主 Agent 系统中，LLM（大语言模型）充当 Agent 的「大脑」，由三个核心组件支撑：

LLM 作为 Agent 的「大脑」，由以下关键组件支撑：

• **规划**：将大型任务分解为子目标，并通过反思（reflection）与精炼（refinement）从错误中学习。

• **记忆**：短期记忆（上下文学习，in-context learning）与长期记忆（外部向量存储，支持持久化回忆）。

• **工具使用**：调用外部 API 获取模型权重中不具备的额外信息或能力。

## 组件一：规划

**任务分解**

**思维链（Chain of Thought, CoT）** 指示模型「逐步思考」，通过增加测试时的计算量将困难任务拆解为简单步骤。同时，CoT 也揭示了模型的推理过程。

**思维树（Tree of Thoughts, ToT）** 扩展了 CoT，在每一步探索多个推理分支，形成树结构。搜索可采用 BFS（广度优先搜索）或 DFS（深度优先搜索），每个状态由一个分类器或多数投票评估。

任务分解可通过 LLM prompt（如 "Steps for XYZ.
1."）、任务特定指令（如 `"Write a story outline."`）或人工输入来实现。

**LLM+P** 使用外部经典规划器，以 PDDL（Planning Domain Definition Language，规划域定义语言）作为中间接口。LLM 将问题翻译为「Problem PDDL」，规划器生成规划方案，LLM 再将结果翻译回自然语言 — 本质上将规划外包给外部工具。

**自我反思**

**ReAct** 通过在动作空间中整合推理与行动，将任务特定的离散动作与自然语言统一。其 prompt 模板遵循以下循环：

```
Thought: ...
Action: ...
Observation: ...
...（多次重复）
```

实验中，ReAct 的表现显著优于仅包含 Action 的基线模型（无 Thought 步骤）。

**Reflexion** 赋予 Agent 动态记忆和自我反思能力以增强推理。采用标准强化学习（RL）设置，使用二元奖励和 ReAct 式动作。每次动作后，Agent 计算一个启发式评估，可依据自我反思重置环境开始新一轮尝试。启发式用于识别低效轨迹或幻觉行为（同样的观察却重复相同动作）。自我反思使用两个（失败轨迹、理想反思）的 few-shot 示例，存入工作记忆（最多三条）。

**后见之明链（Chain of Hindsight, CoH）** 将模型输出序列与人类反馈标注一同呈现给模型，训练其产出逐步改进的结果。训练数据结合了 WebGPT 比较、基于人类反馈的摘要生成和人类偏好数据集。训练中加入正则化项防止过拟合，并随机遮罩 0–5% 的历史 token 以防止走捷径。

**算法蒸馏（Algorithm Distillation, AD）** 将类似思想应用于跨 episode 的 RL 轨迹。模型从串联的多 episode 历史中学习，本质上学习的是 RL 的*过程*而非特定任务的策略。实现近最优的上下文 RL 需要 2–4 个 episode 的多轮上下文。尽管仅使用离线 RL，AD 的性能仍接近 RL²。

## 组件二：记忆

**记忆类型**

人类记忆可分为：

1. **感觉记忆（Sensory Memory）**：保留感官输入的印象数秒（图像、听觉、触觉）。
2. **短期记忆（Short-Term Memory, STM）/ 工作记忆（Working Memory）**：持有约 7 项内容，持续 20–30 秒，用于认知任务。
3. **长期记忆（Long-Term Memory, LTM）**：存储天数到数十年的信息，容量近乎无限。
&nbsp;&nbsp;- *外显/陈述性记忆*：情景记忆（事件）与语义记忆（事实）
&nbsp;&nbsp;- *内隐/程序性记忆*：无意识的技能与习惯

对应到 Agent 系统：
• 感觉记忆 ≈ 原始输入的 embedding 表示
• 短期记忆 ≈ 上下文学习（受限于 context window 大小）
• 长期记忆 ≈ 外部向量存储 + 快速检索

**最大内积搜索（MIPS）**

外部记忆使用支持快速 MIPS 的向量数据库，通常通过近似最近邻（ANN）算法实现：

• **LSH**（Locality-Sensitive Hashing，局部敏感哈希）：通过哈希将相似输入映射到同一桶。
• **ANNOY**（Approximate Nearest Neighbors Oh Yeah）：使用随机投影树。每棵树用超平面切分输入空间；搜索在所有树中遍历最近半区并聚合结果。
• **HNSW**（Hierarchical Navigable Small World，分层可导航小世界）：构建分层小世界图，在层间创建搜索捷径。搜索从顶层开始向下导航。
• **FAISS**（Facebook AI Similarity Search，Facebook AI 相似性搜索）：假设距离服从高斯分布，应用向量量化进行粗聚类后再细聚类。
• **ScaNN**（Scalable Nearest Neighbors，可扩展最近邻）：使用各向异性向量量化来保持内积相似性。

## 组件三：工具使用

**MRKL**（Modular Reasoning, Knowledge and Language，模块化推理、知识与语言）是一种神经-符号架构，通用 LLM 将查询路由给专家模块（可以是神经网络或符号模块，如计算器、天气 API）。实验表明，LLM 在提取基础算术的参数方面存在困难，凸显了知道*何时以及如何使用工具*的关键性。

**TALM** 和 **Toolformer** 对 LM 进行微调以使用外部工具 API，根据 API 调用标注是否提升了输出质量来扩展训练数据集。

ChatGPT 插件和 OpenAI API function calling 是工具增强 LLM 的实践案例。

**HuggingGPT** 使用 ChatGPT 作为任务规划器来选择 HuggingFace 模型。其工作分四个阶段：
1. **任务规划**：LLM 解析用户请求为多个带类型、ID、依赖关系和参数的任务。
2. **模型选择**：LLM 将模型选择转化为多项选择题。
3. **任务执行**：专家模型执行具体任务并记录结果。
4. **响应生成**：LLM 汇总执行结果返回给用户。

挑战包括效率、对长上下文窗口的依赖，以及 LLM 输出和外部服务的稳定性。

**API-Bank** 是一个基准测试，包含 53 个 API 工具、完整的工具增强 LLM 工作流和 264 条标注对话（568 次 API 调用）。它从三个层级评估：
• **Level 1**：给定 API 描述，正确调用 API。
• **Level 2**：通过搜索引擎检索正确的 API，并通过文档学习使用方法。
• **Level 3**：针对模糊的用户请求规划多次 API 调用。

## 案例研究

**科学发现 Agent**

**ChemCrow** 使用 LangChain 和 ReAct 模式，为 LLM 增强 13 种化学工具（有机合成、药物发现、材料设计）。在化学正确性方面，人类专家评分远高于 GPT-4，而基于 LLM 的自动评估则认为两者不相上下 — 这揭示了在需要深度专业知识的领域使用 LLM 做评估的问题。

**Boiko et al. (2023)** 构建了用于自主科学实验的 Agent，覆盖设计、规划和执行。当被要求开发一种新型抗癌药时，Agent 查询趋势、选择靶点、请求骨架结构并尝试合成。在安全测试中，11 个化学武器合成请求中有 4 个被接受。

**生成式 Agent 模拟**

**Generative Agents**（Park et al., 2023）在类似模拟人生的沙盒环境中设置了 25 个 LLM 驱动的虚拟角色。核心组件：

• **记忆流（Memory stream）**：长期外部数据库，以自然语言记录观察。
• **检索模型（Retrieval model）**：基于相关性、时间衰减和重要性获取上下文。
• **反思机制（Reflection mechanism）**：随时间推移将记忆合成为更高层次的推断，通过将最近 100 条观察送入 LM 生成关键问题及答案。
• **规划与反应（Planning & Reacting）**：将反思和环境信息转化为行动，考虑角色关系和跨 Agent 观察。

模拟展现出涌现的社会行为，如信息扩散、关系记忆和事件协调。

**概念验证项目**

**AutoGPT** 使用系统消息包含约束、命令（Google 搜索、文件操作、代码执行等）、资源和性能评估指令。模型以严格 JSON 格式输出思考和指令。

**GPT-Engineer** 从自然语言任务描述生成完整代码仓库。首先通过对话澄清需求，然后切换到代码编写模式，系统消息强调逐步推理、以 markdown 代码块输出完整代码实现和最佳实践（Python 使用 pytest 和 dataclasses；包含 requirements.txt；Node.js 使用 package.json）。

## 挑战

三个关键局限：

• **有限的上下文长度**：限制了历史信息、详细指令和 API 调用上下文的容量。自我反思能从更长的上下文窗口中大幅受益。向量存储虽然提供了访问途径，但其表征能力不如完整的注意力机制。

• **长期规划与任务分解的困难**：LLM 在遇到意外错误时难以调整计划，使其不如通过试错学习的人类鲁棒。

• **自然语言接口的可靠性**：模型输出可能存在格式错误或表现出叛逆行为。大量 Agent 演示代码大量精力花在解析模型输出上。

## 引用与参考文献

*Weng, Lilian. (Jun 2023). "LLM-powered Autonomous Agents". Lil'Log. https://lilianweng.github.io/posts/2023-06-23-agent/.*

BibTeX 引用格式：
```
@article{weng2023agent,
  title = "LLM-powered Autonomous Agents",
  author = "Weng, Lilian",
  journal = "lilianweng.github.io",
  year = "2023",
  month = "Jun",
  url = "https://lilianweng.github.io/posts/2023-06-23-agent/"
}
```

1. Wei et al. "Chain of thought prompting elicits reasoning in large language models." NeurIPS 2022
2. Yao et al. "Tree of Thoughts: Deliberate Problem Solving with Large Language Models." arXiv:2305.10601 (2023)
3. Liu et al. "Chain of Hindsight Aligns Language Models with Feedback." arXiv:2302.02676 (2023)
4. Liu et al. "LLM+P: Empowering Large Language Models with Optimal Planning Proficiency." arXiv:2304.11477 (2023)
5. Yao et al. "ReAct: Synergizing reasoning and acting in language models." ICLR 2023
6. Google Blog. "Announcing ScaNN: Efficient Vector Similarity Search." July 2020
7. Shinn & Labash. "Reflexion: an autonomous agent with dynamic memory and self-reflection." arXiv:2303.11366 (2023)
8. Laskin et al. "In-context Reinforcement Learning with Algorithm Distillation." ICLR 2023
9. Karpas et al. "MRKL Systems: A modular, neuro-symbolic architecture..." arXiv:2205.00445 (2022)
10. Nakano et al. "Webgpt: Browser-assisted question-answering with human feedback." arXiv:2112.09332 (2021)
11. Parisi et al. "TALM: Tool Augmented Language Models." arXiv:2205.12255
12. Schick et al. "Toolformer: Language Models Can Teach Themselves to Use Tools." arXiv:2302.04761 (2023)
13. Li et al. "API-Bank: A Benchmark for Tool-Augmented LLMs." arXiv:2304.08244 (2023)
14. Shen et al. "HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in HuggingFace." arXiv:2303.17580 (2023)
15. Bran et al. "ChemCrow: Augmenting large-language models with chemistry tools." arXiv:2304.05376 (2023)
16. Boiko et al. "Emergent autonomous scientific research capabilities of large language models." arXiv:2304.05332 (2023)
17. Park et al. "Generative Agents: Interactive Simulacra of Human Behavior." arXiv:2304.03442 (2023)
18. AutoGPT. https://github.com/Significant-Gravitas/Auto-GPT
19. GPT-Engineer. https://github.com/AntonOsika/gpt-engineer
