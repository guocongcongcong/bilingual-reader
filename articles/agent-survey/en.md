## Agent 系统概览

Building agents with LLM (large language model) as its core controller is a cool concept. Several proof-of-concepts demos, such as AutoGPT, GPT-Engineer and BabyAGI, serve as inspiring examples. The potentiality of LLM extends beyond generating well-written copies, stories, essays and programs; it can be framed as a powerful general problem solver.

In a LLM-powered autonomous agent system, LLM functions as the agent's brain, complemented by several key components:

**Planning**: Subgoal and decomposition — the agent breaks down large tasks into smaller, manageable subgoals, enabling efficient handling of complex tasks. Reflection and refinement — the agent can do self-criticism and self-reflection over past actions, learn from mistakes and refine them for future steps, thereby improving the quality of final results.

**Memory**: Short-term memory — I would consider all the in-context learning as utilizing short-term memory of the model to learn. Long-term memory — this provides the agent with the capability to retain and recall information over extended periods, often by leveraging an external vector store and fast retrieval.

**Tool use**: The agent learns to call external APIs for extra information that is missing from the model weights (often hard to change after pre-training), including current information, code execution capability, access to proprietary information sources and more.

## 组件一：规划

Chain of thought (CoT; Wei et al. 2022) has become a standard prompting technique for enhancing model performance on complex tasks. The model is instructed to "think step by step" to utilize more test-time computation to decompose hard tasks into smaller and simpler steps. CoT transforms big tasks into multiple manageable tasks and sheds light into an interpretation of the model's thinking process.

Tree of Thoughts (Yao et al. 2023) extends CoT by exploring multiple reasoning possibilities at each step. It first decomposes the problem into multiple thought steps and generates multiple thoughts per step, creating a tree structure. The search process can be BFS (breadth-first search) or DFS (depth-first search) with each state evaluated by a classifier (via a prompt) or majority vote.

Task decomposition can be done (1) by LLM with simple prompting like "Steps for XYZ.
1.", "What are the subgoals for achieving XYZ?", (2) by using task-specific instructions; e.g. "Write a story outline." for writing a novel, or (3) with human inputs.

Another quite distinct approach, LLM+P (Liu et al. 2023), involves relying on an external classical planner to do long-horizon planning. This approach utilizes the Planning Domain Definition Language (PDDL) as an intermediate interface to describe the planning problem. In this process, LLM (1) translates the problem into "Problem PDDL", then (2) requests a classical planner to generate a PDDL plan based on an existing "Domain PDDL", and finally (3) translates the PDDL plan back into natural language. Essentially, the planning step is outsourced to an external tool, assuming the availability of domain-specific PDDL and a suitable planner.

ReAct (Yao et al. 2023) integrates reasoning and acting within LLM by extending the action space to be a combination of task-specific discrete actions and the language space. The former enables LLM to interact with the environment (e.g. use Wikipedia search API), while the latter prompting LLM to generate reasoning traces in natural language. The ReAct prompt template incorporates explicit steps for LLM to think, roughly formatted as:

Thought: ...
Action: ...
Observation: ...
... (Repeated many times)

In both experiments on knowledge-intensive tasks and decision-making tasks, ReAct works better than the Act-only baseline where Thought: ... step is removed.

Reflexion (Shinn & Labash 2023) is a framework to equip agents with dynamic memory and self-reflection capabilities to improve reasoning skills. Reflexion has a standard RL setup, in which the reward model provides a simple binary reward and the action space follows the setup in ReAct. After each action, the agent computes a heuristic and optionally may decide to reset the environment to start a new trial depending on the self-reflection results. The heuristic function determines when the trajectory is inefficient or contains hallucination and should be stopped. Inefficient planning refers to trajectories that take too long without success. Hallucination is defined as encountering a sequence of consecutive identical actions that lead to the same observation in the environment. Self-reflection is created by showing two-shot examples to LLM and each example is a pair of (failed trajectory, ideal reflection for guiding future changes in the plan). Then reflections are added into the agent's working memory, up to three, to be used as context for querying LLM.

Chain of Hindsight (CoH; Liu et al. 2023) encourages the model to improve on its own outputs by explicitly presenting it with a sequence of past outputs, each annotated with feedback. Human feedback data is a collection where each prompt has model completions with human ratings and hindsight feedback, ranked by reward. The model is finetuned to predict only the best output conditioned on the feedback sequence, so that the model can self-reflect to produce better output. To avoid overfitting, CoH adds a regularization term to maximize the log-likelihood of the pre-training dataset. To avoid shortcutting, they randomly mask 0% - 5% of past tokens during training. The training dataset combines WebGPT comparisons, summarization from human feedback and human preference datasets.

Algorithm Distillation (AD; Laskin et al. 2023) applies the same idea to cross-episode trajectories in reinforcement learning tasks, where an algorithm is encapsulated in a long history-conditioned policy. Considering that an agent interacts with the environment many times and in each episode the agent gets a little better, AD concatenates this learning history and feeds that into the model. The goal is to learn the process of RL instead of training a task-specific policy itself. Multi-episodic contexts of 2-4 episodes are necessary to learn a near-optimal in-context RL algorithm. AD demonstrates in-context RL with performance getting close to RL^2 despite only using offline RL and learns much faster than other baselines.

## 组件二：记忆

Memory can be defined as the processes used to acquire, store, retain, and later retrieve information. There are several types of memory in human brains.

**Sensory Memory**: This is the earliest stage of memory, providing the ability to retain impressions of sensory information (visual, auditory, etc) after the original stimuli have ended. Sensory memory typically only lasts for up to a few seconds. Subcategories include iconic memory (visual), echoic memory (auditory), and haptic memory (touch).
**Short-Term Memory (STM) or Working Memory**: It stores information that we are currently aware of and needed to carry out complex cognitive tasks such as learning and reasoning. Short-term memory is believed to have the capacity of about 7 items (Miller 1956) and lasts for 20-30 seconds.
**Long-Term Memory (LTM)**: Long-term memory can store information for a remarkably long time, ranging from a few days to decades, with an essentially unlimited storage capacity. There are two subtypes: Explicit / declarative memory (episodic memory for events and experiences, semantic memory for facts and concepts) and Implicit / procedural memory (unconscious skills and routines performed automatically).

We can roughly consider the following mappings:
Sensory memory as learning embedding representations for raw inputs, including text, image or other modalities;
Short-term memory as in-context learning. It is short and finite, as it is restricted by the finite context window length of Transformer.
Long-term memory as the external vector store that the agent can attend to at query time, accessible via fast retrieval.

The external memory can alleviate the restriction of finite attention span. A standard practice is to save the embedding representation of information into a vector store database that can support fast maximum inner-product search (MIPS). To optimize the retrieval speed, the common choice is the approximate nearest neighbors (ANN) algorithm to return approximately top k nearest neighbors to trade off a little accuracy lost for a huge speedup.

**LSH** (Locality-Sensitive Hashing): It introduces a hashing function such that similar input items are mapped to the same buckets with high probability, where the number of buckets is much smaller than the number of inputs.
**ANNOY** (Approximate Nearest Neighbors Oh Yeah): The core data structure are random projection trees, a set of binary trees where each non-leaf node represents a hyperplane splitting the input space into half and each leaf stores one data point. Trees are built independently and at random. ANNOY search happens in all the trees to iteratively search through the half that is closest to the query and then aggregates the results.
**HNSW** (Hierarchical Navigable Small World): It is inspired by the idea of small world networks. HNSW builds hierarchical layers of small-world graphs, where the bottom layers contain the actual data points. The layers in the middle create shortcuts to speed up search. When performing a search, HNSW starts from a random node in the top layer and navigates towards the target, moving down to the next layer when it cannot get any closer.
**FAISS** (Facebook AI Similarity Search): It operates on the assumption that in high dimensional space, distances between nodes follow a Gaussian distribution and thus there should exist clustering of data points. FAISS applies vector quantization by partitioning the vector space into clusters and then refining the quantization within clusters.
**ScaNN** (Scalable Nearest Neighbors): The main innovation in ScaNN is anisotropic vector quantization. It quantizes a data point such that the inner product is as similar to the original distance as possible, instead of picking the closest quantization centroid points.

## 组件三：工具使用

MRKL (Karpas et al. 2022), short for "Modular Reasoning, Knowledge and Language", is a neuro-symbolic architecture for autonomous agents. A MRKL system is proposed to contain a collection of "expert" modules and the general-purpose LLM works as a router to route inquiries to the best suitable expert module. These modules can be neural (e.g. deep learning models) or symbolic (e.g. math calculator, currency converter, weather API). Their experiments showed that it was harder to solve verbal math problems than explicitly stated math problems because LLMs failed to extract the right arguments for the basic arithmetic reliably. The results highlight that when the external symbolic tools can work reliably, knowing when to and how to use the tools are crucial, determined by the LLM capability.

Both TALM (Tool Augmented Language Models; Parisi et al. 2022) and Toolformer (Schick et al. 2023) fine-tune a LM to learn to use external tool APIs. The dataset is expanded based on whether a newly added API call annotation can improve the quality of model outputs.

ChatGPT Plugins and OpenAI API function calling are good examples of LLMs augmented with tool use capability working in practice. The collection of tool APIs can be provided by other developers (as in Plugins) or self-defined (as in function calls).

HuggingGPT (Shen et al. 2023) is a framework to use ChatGPT as the task planner to select models available in HuggingFace platform according to the model descriptions and summarize the response based on the execution results. The system comprises of 4 stages: (1) Task planning: LLM works as the brain and parses the user requests into multiple tasks with task type, ID, dependencies, and arguments. (2) Model selection: LLM distributes the tasks to expert models, where the request is framed as a multiple-choice question. (3) Task execution: Expert models execute on the specific tasks and log results. (4) Response generation: LLM receives the execution results and provides summarized results to users.

To put HuggingGPT into real world usage, a couple challenges need to solve: (1) Efficiency improvement is needed as both LLM inference rounds and interactions with other models slow down the process; (2) It relies on a long context window to communicate over complicated task content; (3) Stability improvement of LLM outputs and external model services.

API-Bank (Li et al. 2023) is a benchmark for evaluating the performance of tool-augmented LLMs. It contains 53 commonly used API tools, a complete tool-augmented LLM workflow, and 264 annotated dialogues that involve 568 API calls. The selection of APIs is quite diverse, including search engines, calculator, calendar queries, smart home control, schedule management, health data management, account authentication workflow and more. This benchmark evaluates the agent's tool use capabilities at three levels: Level-1 evaluates the ability to call the API given its description. Level-2 examines the ability to retrieve the API by searching and learning from documentation. Level-3 assesses the ability to plan API beyond retrieve and call, handling unclear user requests with multiple API calls.

## 案例研究

ChemCrow (Bran et al. 2023) is a domain-specific example in which LLM is augmented with 13 expert-designed tools to accomplish tasks across organic synthesis, drug discovery, and materials design. The workflow, implemented in LangChain, reflects what was previously described in the ReAct and MRKLs and combines CoT reasoning with tools relevant to the tasks. The LLM is provided with a list of tool names, descriptions of their utility, and details about the expected input/output. It is then instructed to answer a user-given prompt using the tools provided when necessary, following the ReAct format - Thought, Action, Action Input, Observation. One interesting observation is that while the LLM-based evaluation concluded that GPT-4 and ChemCrow perform nearly equivalently, human evaluations with experts showed that ChemCrow outperforms GPT-4 by a large margin. This indicates a potential problem with using LLM to evaluate its own performance on domains that require deep expertise.

Boiko et al. (2023) also looked into LLM-empowered agents for scientific discovery, to handle autonomous design, planning, and performance of complex scientific experiments. This agent can use tools to browse the Internet, read documentation, execute code, call robotics experimentation APIs and leverage other LLMs. For example, when requested to "develop a novel anticancer drug", the model: inquired about current trends in anticancer drug discovery; selected a target; requested a scaffold targeting these compounds; once the compound was identified, attempted its synthesis. They also discussed risks: they developed a test set containing known chemical weapon agents. 4 out of 11 requests (36%) were accepted to obtain a synthesis solution; 7 out of 11 were rejected.

Generative Agents (Park, et al. 2023) is super fun experiment where 25 virtual characters, each controlled by a LLM-powered agent, are living and interacting in a sandbox environment, inspired by The Sims. Generative agents create believable simulacra of human behavior for interactive applications. The design of generative agents combines LLM with memory, planning and reflection mechanisms to enable agents to behave conditioned on past experience, as well as to interact with other agents.

**Memory stream**: is a long-term memory module (external database) that records a comprehensive list of agents' experience in natural language. Each element is an observation, an event directly provided by the agent. Inter-agent communication can trigger new natural language statements.
**Retrieval model**: surfaces the context to inform the agent's behavior, according to relevance, recency and importance. Recency: recent events have higher scores. Importance: distinguish mundane from core memories, ask LM directly. Relevance: based on how related it is to the current situation / query.
**Reflection mechanism**: synthesizes memories into higher level inferences over time and guides the agent's future behavior. They are higher-level summaries of past events. Prompt LM with 100 most recent observations and to generate 3 most salient high-level questions, then ask LM to answer those questions.
**Planning & Reacting**: translate the reflections and the environment information into actions. Planning is essentially in order to optimize believability at the moment vs in time. Relationships between agents and observations of one agent by another are all taken into consideration for planning and reacting.

This fun simulation results in emergent social behavior, such as information diffusion, relationship memory (e.g. two agents continuing the conversation topic) and coordination of social events (e.g. host a party and invite many others).

AutoGPT has drawn a lot of attention into the possibility of setting up autonomous agents with LLM as the main controller. It has quite a lot of reliability issues given the natural language interface, but nevertheless a cool proof-of-concept demo. A lot of code in AutoGPT is about format parsing. The system message includes constraints, commands (Google Search, file operations, code execution, etc.), resources and performance evaluation instructions. The model outputs thoughts and instructions in strict JSON format.

GPT-Engineer is another project to create a whole repository of code given a task specified in natural language. The GPT-Engineer is instructed to think over a list of smaller components to build and ask for user input to clarify questions as needed. After clarification, the agent moves into code writing mode with a different system message emphasizing step-by-step reasoning, outputting complete code implementation in markdown code blocks and following best practices (e.g. for Python: pytest and dataclasses; include requirements.txt; for NodeJS: package.json).

## 挑战

After going through key ideas and demos of building LLM-centered agents, I start to see a couple common limitations:

**Finite context length**: The restricted context capacity limits the inclusion of historical information, detailed instructions, API call context, and responses. The design of the system has to work with this limited communication bandwidth, while mechanisms like self-reflection to learn from past mistakes would benefit a lot from long or infinite context windows. Although vector stores and retrieval can provide access to a larger knowledge pool, their representation power is not as powerful as full attention.

**Challenges in long-term planning and task decomposition**: Planning over a lengthy history and effectively exploring the solution space remain challenging. LLMs struggle to adjust plans when faced with unexpected errors, making them less robust compared to humans who learn from trial and error.

**Reliability of natural language interface**: Current agent system relies on natural language as an interface between LLMs and external components such as memory and tools. However, the reliability of model outputs is questionable, as LLMs may make formatting errors and occasionally exhibit rebellious behavior (e.g. refuse to follow an instruction). Consequently, much of the agent demo code focuses on parsing model output.

## 引用与参考文献

Cited as:

Weng, Lilian. (Jun 2023). "LLM-powered Autonomous Agents". Lil'Log. https://lilianweng.github.io/posts/2023-06-23-agent/.

@article{weng2023agent,
  title = "LLM-powered Autonomous Agents",
  author = "Weng, Lilian",
  journal = "lilianweng.github.io",
  year = "2023",
  month = "Jun",
  url = "https://lilianweng.github.io/posts/2023-06-23-agent/"
}

[1] Wei et al. "Chain of thought prompting elicits reasoning in large language models." NeurIPS 2022
[2] Yao et al. "Tree of Thoughts: Deliberate Problem Solving with Large Language Models." arXiv:2305.10601 (2023)
[3] Liu et al. "Chain of Hindsight Aligns Language Models with Feedback." arXiv:2302.02676 (2023)
[4] Liu et al. "LLM+P: Empowering Large Language Models with Optimal Planning Proficiency." arXiv:2304.11477 (2023)
[5] Yao et al. "ReAct: Synergizing reasoning and acting in language models." ICLR 2023
[6] Google Blog. "Announcing ScaNN: Efficient Vector Similarity Search." July 2020
[7] Shinn & Labash. "Reflexion: an autonomous agent with dynamic memory and self-reflection." arXiv:2303.11366 (2023)
[8] Laskin et al. "In-context Reinforcement Learning with Algorithm Distillation." ICLR 2023
[9] Karpas et al. "MRKL Systems: A modular, neuro-symbolic architecture..." arXiv:2205.00445 (2022)
[10] Nakano et al. "Webgpt: Browser-assisted question-answering with human feedback." arXiv:2112.09332 (2021)
[11] Parisi et al. "TALM: Tool Augmented Language Models." arXiv:2205.12255
[12] Schick et al. "Toolformer: Language Models Can Teach Themselves to Use Tools." arXiv:2302.04761 (2023)
[13] Li et al. "API-Bank: A Benchmark for Tool-Augmented LLMs." arXiv:2304.08244 (2023)
[14] Shen et al. "HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in HuggingFace." arXiv:2303.17580 (2023)
[15] Bran et al. "ChemCrow: Augmenting large-language models with chemistry tools." arXiv:2304.05376 (2023)
[16] Boiko et al. "Emergent autonomous scientific research capabilities of large language models." arXiv:2304.05332 (2023)
[17] Park et al. "Generative Agents: Interactive Simulacra of Human Behavior." arXiv:2304.03442 (2023)
[18] AutoGPT. https://github.com/Significant-Gravitas/Auto-GPT
[19] GPT-Engineer. https://github.com/AntonOsika/gpt-engineer