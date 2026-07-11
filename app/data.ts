Exit code: 0
Wall time: 0.3 seconds
Output:
export type Article = {
  slug: string;
  date: string;
  issue: string;
  title: string;
  titleEn: string;
  authors: string;
  journal: string;
  year: number;
  volume: string;
  pages: string;
  doi: string;
  sourceUrl: string;
  documentUrl: string;
  language: "英文" | "中文";
  method: "质性研究" | "定量研究" | "综述" | "混合研究";
  topics: string[];
  recommendation: string;
  selectionSource?: string;
  articleStructure?: string[];
  question: string;
  thesis: string;
  theory: { name: string; detail: string }[];
  methods: string[];
  chain: { label: string; detail: string }[];
  findings: string[];
  highlights: { label: string; detail: string }[];
  limits: string[];
  questions: string[];
  terms: { term: string; definition: string }[];
};

export const articles: Article[] = [
  {
    slug: "human-chatbot-interaction-sociology",
    date: "2026-07-11",
    issue: "第 02 期",
    title: "社会学如何推进人—聊天机器人互动研究",
    titleEn: "Perspectives on How Sociology Can Advance Theorizing about Human-Chatbot Interaction and Developing Chatbots for Social Good",
    authors: "Celeste Campos-Castillo · Xuan Kang · Linnea I. Laestadius",
    journal: "arXiv preprint",
    year: 2025,
    volume: "arXiv:2507.05030",
    pages: "预印本",
    doi: "暂无 DOI",
    sourceUrl: "https://arxiv.org/abs/2507.05030",
    documentUrl: "/documents/2026-07-11-human-chatbot-sociology.docx",
    language: "英文",
    method: "综述",
    topics: ["人机互动", "聊天机器人", "数字社会学", "技术公平"],
    recommendation: "这篇文章示范社会学如何进入一个由计算机科学、传播学和公共卫生主导的新议题，把人与聊天机器人的互动重新放回资源分配、权力关系、文化规范和健康不平等之中。",
    question: "为什么社会学在聊天机器人研究中参与不足？社会结构如何塑造不同群体对聊天机器人的使用和依赖？社会学理论又如何帮助降低安全风险并提升技术公平？",
    thesis: "作者从社会学在聊天机器人研究中的参与不足出发，提出资源替代理论、权力—依赖理论、情感控制理论和疾病根本原因理论四条分析路径，连接使用动因、互动风险、文化适配与技术公平。",
    theory: [
      { name: "资源替代理论", detail: "替代性资源越少，单一资源满足需求的重要性越高；教育、陪伴或医疗资源较少的群体可能更依赖聊天机器人。" },
      { name: "权力—依赖理论", detail: "对一项资源的需要越强、替代选择越少，依赖越不对称；持续在线和低拒绝可能增强对聊天机器人的依赖。" },
      { name: "情感控制理论", detail: "人们试图维持身份、行为和情境的文化情感意义；回应若违背群体规范，可能造成失配、疏离或伤害。" },
      { name: "疾病根本原因理论", detail: "社会资源决定人们利用新知识和技术改善健康的能力，因此技术创新也可能扩大既有差距。" },
    ],
    methods: [
      "本文不是传统实证论文，而是理论透视与跨学科文献综合。",
      "作者用 Web of Science 检索结果描述聊天机器人研究的学科分布。",
      "文章将传播学、公共卫生、社会心理学和技术研究中的发现与四种社会学理论对应。",
      "文中命题仍需后续问卷、访谈、实验或参与式设计研究检验。",
    ],
    chain: [
      { label: "学科缺口", detail: "聊天机器人研究迅速增长，但社会学参与明显不足。" },
      { label: "解释不足", detail: "现有研究多集中个体需求和技术接受，忽略需求的社会生成。" },
      { label: "结构机制", detail: "资源不平等塑造谁更需要聊天机器人、谁从中获益或受损。" },
      { label: "互动机制", detail: "依赖、身份与情感失配需要微观社会学解释。" },
      { label: "设计与治理", detail: "社会学应进入理论建构、产品设计、参与式测试和政策治理。" },
    ],
    findings: [
      "人—聊天机器人互动看似私人化，实际上深受社会结构与文化规范影响。",
      "资源不足可能提高特定群体对聊天机器人的使用和依赖。",
      "聊天机器人的持续可用与低拒绝可能形成新的权力不对称。",
      "社会学理论能够帮助识别文化失配、依赖风险和不平等后果。",
      "社会学应进入技术设计和测试，而不仅进行事后批评。",
    ],
    highlights: [
      { label: "选题", detail: "从学科参与不足切入，说明社会学对新技术议题的独特价值。" },
      { label: "理论", detail: "把四种经典理论转化为可检验的新技术研究命题。" },
      { label: "尺度", detail: "同时连接宏观资源结构与微观互动过程。" },
      { label: "应用", detail: "把安全与公平连接到产品设计、参与式测试和公共政策。" },
    ],
    limits: [
      "当前为 arXiv 预印本，不能确认已经通过同行评审。",
      "没有独立实证数据，部分论断属于理论推演。",
      "例证多来自美国社会，未必能直接移植到中国。",
      "对商业平台、数据所有权与算法权力讨论不足。",
    ],
    questions: [
      "在中国高校中，哪些资源不足可能促使学生更依赖聊天机器人？",
      "聊天机器人的持续在线和较少拒绝为什么可能形成权力不对称？",
      "如果开发大学生心理支持机器人，如何分别运用情感控制理论和疾病根本原因理论？",
    ],
    terms: [
      { term: "资源替代", definition: "一种资源在缺少其他替代资源时，对个体结果产生更大作用的机制。" },
      { term: "权力—依赖", definition: "一方越依赖另一方掌握的资源，另一方在关系中的权力通常越大。" },
      { term: "情感控制", definition: "行动者通过行为维持身份和情境的文化情感意义。" },
      { term: "疾病根本原因", definition: "社会经济资源持续影响人们规避风险和利用健康创新的能力。" },
      { term: "参与式设计", definition: "让目标使用者和相关社群参与技术定义、开发、测试与评估。" },
    ],
  },
  {
    slug: "between-two-rituals",
    date: "2026-07-10",
    issue: "第 01 期",
    title: "两种仪式之间",
    titleEn: "Between Two Rituals: Face and Effervescence as Moments of Social Life",
    authors: "Anders Vassenden · Nicholas Hoynes · Taylor Price · Iddo Tavory",
    journal: "American Sociological Review",
    year: 2026,
    volume: "91(3)",
    pages: "379–404",
    doi: "10.1177/00031224261441865",
    sourceUrl: "https://journals.sagepub.com/doi/full/10.1177/00031224261441865",
    documentUrl: "/documents/2026-07-10-sociology-daily-reading.docx",
    language: "英文",
    method: "质性研究",
    topics: ["互动仪式", "微观社会学", "族裔关系", "创造力"],
    recommendation: "这篇文章最值得学习的，不是‘戈夫曼与柯林斯分别说了什么’，而是作者如何把理论分歧转化为可观察的经验问题，再利用两个异质案例建立可迁移的分析模型。",
    question: "面子仪式与集体欢腾仪式如何在不同社会情境中分离、转换并相互支撑？这种微观过程又如何累积为群体边界、组织合作和社会运动等更大尺度结果？",
    thesis: "社会学常把戈夫曼与柯林斯笔下的‘互动仪式’视为同一机制。本文将其区分为维护自我与互动秩序的面子仪式，以及产生共同注意、共享情绪与团结的集体欢腾仪式，并进一步研究二者的关系与轨迹。",
    theory: [
      { name: "面子仪式", detail: "行动者通过礼貌、克制、回避冲突和情境修复，维护自己与他人的道德价值，使互动得以继续。" },
      { name: "集体欢腾仪式", detail: "共同注意与共享情绪相互强化，形成兴奋、同步、团结和继续参与的情绪能量。" },
      { name: "仪式轨迹", detail: "两类仪式不是静态标签，而会跨受众分隔，或在同一情境内按顺序递归并形成反馈循环。" },
    ],
    methods: [
      "挪威族裔污名研究：32名参与者、39次深度访谈，结合开放式提问与情境短文。",
      "多伦多歌曲创作民族志：三年参与观察，追踪20名创作者和47场创作活动。",
      "25场创作有音视频记录，累计超过30小时，并辅以37次深度访谈。",
      "编码关注污名情境、受众差异、轮流发言、热情、犹豫和互动修复。",
    ],
    chain: [
      { label: "概念缺口", detail: "同一术语内部隐藏着两套不同的行动者假设和社会机制。" },
      { label: "案例一：分隔", detail: "少数族裔面对多数群体时更强调面子维护，在少数群体内部则更可能形成共同情绪。" },
      { label: "案例二：递归", detail: "尊重与克制为冒险表达创造安全，集体兴奋又鼓励新的脆弱表达。" },
      { label: "理论外推", detail: "微观仪式的顺序和反馈可能塑造社会运动、组织承诺、关系变化与网络边界。" },
    ],
    findings: [
      "戈夫曼式面子仪式和柯林斯式集体欢腾仪式是不同机制，不能笼统合并。",
      "两种仪式可以随受众分隔，也可以在同一互动中依次出现并相互强化。",
      "面子维护为共同注意和欢腾创造条件，欢腾则支撑进一步的脆弱表达。",
      "未来研究应考察仪式的类型、顺序、节奏与时间变化，即‘仪式轨迹’。",
    ],
    highlights: [
      { label: "选题", detail: "从经典理论共享术语却解释不同过程的‘细缝’进入。" },
      { label: "结构", detail: "两个案例各司其职：一个解释跨情境分隔，一个解释情境内递归。" },
      { label: "方法", detail: "访谈捕捉稀少事件及事后叙述，音视频民族志捕捉节奏、停顿与修复。" },
      { label: "论证", detail: "成功互动与失败片段并置，让机制条件比单纯成功故事更清楚。" },
    ],
    limits: [
      "污名互动主要依赖回溯性访谈，无法完全还原现场的语调、停顿和身体动作。",
      "两个案例是独立项目后期对话，并非统一设计下的严格比较。",
      "少数族裔样本中高学历者较多，歌曲创作网络则男性居多，代表性有限。",
      "从微观反馈循环推向宏观网络和社会运动，仍需要纵向与跨情境证据。",
    ],
    questions: [
      "如果保护对方的面子会让歧视不被指出，它是在维护秩序，还是在再生产不平等？",
      "最大差异案例设计与同一场域内的群体比较相比，各自的优势和风险是什么？",
      "怎样用可观察的证据区分礼貌的面子工作和真正的情绪团结？",
    ],
    terms: [
      { term: "互动秩序", definition: "面对面或共同在场的互动具有相对独立的规则与结构。" },
      { term: "面子", definition: "个人在特定互动中被认可的积极社会价值。" },
      { term: "集体欢腾", definition: "共同注意与共享情绪相互强化时形成的团结和情绪能量。" },
      { term: "情境修复", definition: "参与者通过澄清、道歉或改述恢复可继续的互动。" },
    ],
  },
];

export const getArticle = (slug: string) => articles.find((article) => article.slug === slug);

