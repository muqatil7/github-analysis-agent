# GitHub Analysis Agent 🤖

مشروع ذكي لتحليل مستودعات GitHub باستخدام **LangGraph** + **LangChain** + **LangSmith** مع دعم **MCP (Model Context Protocol)**.

## ✨ المميزات الرئيسية

- 🔍 **تحليل شامل لمستودعات GitHub**: تحليل الكود، الأمان، التوثيق، والتبعيات
- 🤖 **AI Agent متطور**: يستخدم أحدث تقنيات LangGraph للتفاعل الذكي
- 📊 **مراقبة متقدمة**: تتبع كامل باستخدام LangSmith
- 🔄 **إدارة Context ذكية**: تلخيص تلقائي عند الاقتراب من حد الـ tokens (200k)
- 🔗 **تكامل MCP**: اتصال مباشر مع GitHub عبر Model Context Protocol
- 🎯 **أنواع تحليل متعددة**: ملخص، أمان، مراجعة كود، توثيق، تبعيات، مخصص

## 🚀 التثبيت والإعداد

### 1. استنساخ المستودع
```bash
git clone https://github.com/muqatil7/github-analysis-agent.git
cd github-analysis-agent
```

### 2. إنشاء البيئة الافتراضية
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate  # Windows
```

### 3. تثبيت التبعيات
```bash
pip install -r requirements.txt
```

### 4. إعداد متغيرات البيئة
```bash
cp .env.example .env
```

قم بتحرير ملف `.env` وإضافة المفاتيح المطلوبة:

```env
# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=github-analysis-agent

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# GitHub Configuration
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token_here

# Application Settings
MAX_CONTEXT_TOKENS=200000
SUMMARY_TOKEN_THRESHOLD=180000
KEEP_LAST_MESSAGES=5
```

## 📖 الاستخدام

### الوضع التفاعلي (موصى به)
```bash
python main.py
```

### وضع سطر الأوامر
```bash
# تحليل أساسي
python main.py https://github.com/owner/repo

# تحليل أمني مخصص
python main.py https://github.com/owner/repo -t security -s "Focus on security vulnerabilities"

# تحليل مع رسالة مخصصة
python main.py https://github.com/owner/repo -t code_review -u "Review the main.py file for best practices"
```

### الاستخدام البرمجي
```python
import asyncio
from src.agents.github_agent import GitHubAnalysisAgent
from src.core.models import AnalysisType

async def analyze_repo():
    agent = GitHubAnalysisAgent()
    await agent.initialize()
    
    result = await agent.analyze(
        repository_url="https://github.com/owner/repo",
        analysis_type=AnalysisType.SECURITY,
        system_prompt="Focus on security vulnerabilities",
        user_prompt="Provide detailed security assessment"
    )
    
    print(result.current_analysis.summary)
    await agent.close()

# تشغيل التحليل
asyncio.run(analyze_repo())
```

## 🏗️ هيكل المشروع

```
github-analysis-agent/
├── src/
│   ├── core/
│   │   ├── config.py          # إدارة الإعدادات
│   │   ├── models.py          # نماذج البيانات
│   │   └── context_manager.py # إدارة السياق والذاكرة
│   ├── agents/
│   │   ├── github_agent.py    # الوكيل الرئيسي
│   │   └── mcp_client.py      # عميل MCP
│   ├── utils/
│   │   ├── token_counter.py   # حساب الرموز المميزة
│   │   └── validators.py      # التحقق من المدخلات
│   └── workflows/
│       ├── graph_builder.py   # بناء سير العمل
│       └── state_management.py # إدارة الحالة
├── main.py                    # نقطة الدخول الرئيسية
├── requirements.txt           # التبعيات
├── .env.example              # مثال متغيرات البيئة
└── README.md                 # التوثيق
```

## 🔍 أنواع التحليل المدعومة

| النوع | الوصف |
|-------|--------|
| `summary` | ملخص عام للمستودع |
| `security` | تحليل الثغرات الأمنية |
| `code_review` | مراجعة جودة الكود |
| `documentation` | تقييم التوثيق |
| `dependencies` | تحليل التبعيات |
| `custom` | تحليل مخصص حسب الطلب |

## ⚙️ الميزات المتقدمة

### إدارة السياق الذكية
- **حد الرموز المميزة**: 200,000 token (قابل للتخصيص)
- **التلخيص التلقائي**: عند الوصول إلى 180,000 token
- **الاحتفاظ بالرسائل**: آخر 5 رسائل تبقى كما هي

### مراقبة LangSmith
- تتبع تلقائي لجميع العمليات
- مراقبة الأداء والتكلفة
- تتبع التجارب والتحسينات

### تكامل MCP
- اتصال مباشر مع GitHub
- أدوات متقدمة لتحليل المستودعات
- دعم العمليات غير المتزامنة

## 🔧 التطوير والتخصيص

### إضافة نوع تحليل جديد
1. أضف النوع إلى `AnalysisType` في `src/core/models.py`
2. أنشئ عقدة تحليل جديدة في `src/agents/analysis_nodes.py`
3. حدث منطق الـ system prompt في `src/agents/github_agent.py`

### إضافة أدوات MCP جديدة
1. حدث `src/agents/mcp_client.py`
2. أضف الطرق الجديدة للتفاعل مع MCP server
3. اربط الأدوات بسير العمل في `GitHubAnalysisAgent`

## 📊 مراقبة الأداء

### LangSmith Dashboard
- انتقل إلى [LangSmith](https://smith.langchain.com)
- اختر مشروعك `github-analysis-agent`
- راقب المقاييس والتتبعات

### السجلات المحلية
```bash
tail -f github_agent.log
```

## 🤝 المساهمة

1. Fork المشروع
2. أنشئ branch للميزة الجديدة (`git checkout -b feature/amazing-feature`)
3. Commit التغييرات (`git commit -m 'Add amazing feature'`)
4. Push إلى البranch (`git push origin feature/amazing-feature`)
5. افتح Pull Request

## 📄 الترخيص

هذا المشروع مرخص تحت رخصة MIT. راجع ملف `LICENSE` للتفاصيل.

## 🙋‍♂️ الدعم

- **Issues**: [GitHub Issues](https://github.com/muqatil7/github-analysis-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/muqatil7/github-analysis-agent/discussions)

## 🔗 روابط مفيدة

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [LangSmith Documentation](https://docs.langchain.com/langsmith/)
- [MCP Protocol](https://modelcontextprotocol.io/)

---

**تم التطوير بواسطة [Yahya Sayed](https://github.com/muqatil7)** 🚀