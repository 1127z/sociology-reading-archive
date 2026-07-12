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
  evidenceBasis?: "全文" | "摘要";
  analysisDepth?: "专家精读" | "摘要解读";
  fullTextSource?: string;
  confidence?: "高" | "中" | "低";
  difficultyLevel?: "L1" | "L2" | "L3" | "L4";
  selectionScore?: number;
  selectionBreakdown?: Record<string, number>;
  learningFocus?: string;
  prerequisiteKnowledge?: string[];
  readingGuide?: { quickRead: string; closeRead: string; canSkim: string };
  learningExercises?: string[];
  fieldPosition?: string;
  literatureDialogue?: string[];
  empiricalContribution?: string;
  theoreticalContribution?: string;
  methodologicalContribution?: string;
  contentFeatures?: { label: string; detail: string }[];
  researchFeatures?: { label: string; detail: string }[];
  criticalReview?: string[];
  researchImplications?: string[];
  evidenceBoundaries?: string[];
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

export const articles: Article[] = [];

export const getArticle = (slug: string) => articles.find((article) => article.slug === slug);



