# CodePrompt-DSL v2 完整任务定义

> **版本**：v2.0 | **日期**：2026-03-31  
> **用途**：定义全部 60 个实验任务的需求、约束和验证方式，确保第三方可完整复现  
> **设计原则**：  
> 1. 每类 20 个任务，难度分三档：基础(8) / 中等(8) / 进阶(4)  
> 2. 每个任务的约束配置不完全相同，覆盖约束字段的多种组合  
> 3. 每个任务有明确的可执行验证方式

---

## 一、约束字段说明

每个任务都附带一组显式工程约束。这些约束就是 Compact Header 要压缩的对象。

| 字段 | 含义 | 可选值 |
|------|------|--------|
| language | 编程语言 | TypeScript / Python |
| framework | 框架 | React / FastAPI / None(纯Python) |
| form | 输出形式 | single_file_component / single_module / cli_script / function_library |
| style | 样式方案 | tailwind / plain_css / not_applicable |
| dependencies | 依赖限制 | no_external / stdlib_only / allow:{具体库} |
| layout | 布局 | mobile_first / responsive / desktop / not_applicable |
| data | 数据来源 | mock / not_applicable |
| output | 输出要求 | code_only |
| tests | 是否含测试 | true / false |
| comments | 是否含注释 | true / false |

---

## 二、Frontend 任务（FE-01 ~ FE-20）

**统一技术栈**：React + TypeScript，单文件组件，`export default`  
**验证方式**：`tsc --noEmit` 编译检查 + AST 结构检查

### 基础难度（FE-01 ~ FE-08）

#### FE-01 登录表单
- **需求**：做一个登录表单，包含邮箱输入框、密码输入框、登录按钮。要有基本的输入验证（邮箱格式、密码非空），验证不通过时显示错误提示。
- **古文需求**：作登入表，含邮密二栏与登入键。须校邮之格式、验密之非空，不合则示误。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=mobile_first, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有 form 元素、有 email input、有 password input、有 submit button、有错误提示容器

#### FE-02 待办事项列表
- **需求**：做一个待办事项应用，可以添加新任务、删除已有任务、标记任务为已完成、按完成状态筛选显示。
- **古文需求**：作待办页，具增删之能，可标毕，可按状筛示。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=mobile_first, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有输入框、有添加按钮、有列表渲染、有删除功能、有完成切换、有筛选控件

#### FE-03 用户资料卡片
- **需求**：做一个用户资料卡片组件，显示头像、用户名、个人简介、关注按钮。关注按钮点击后在"关注"和"已关注"之间切换。
- **古文需求**：作用户卡，示头像、名、简介与关注键。点关注则切"已关注"。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=mobile_first, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有头像展示、有用户名、有简介文字、有按钮且可切换状态

#### FE-04 计数器面板
- **需求**：做一个计数器，包含当前计数显示、加一按钮、减一按钮、重置按钮。计数不能低于零。
- **古文需求**：作计数器，示当前数。具增、减、归零三键。数不可负。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=plain_css, dependencies=no_external, layout=responsive, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有数字显示、有三个按钮、有最小值限制逻辑

#### FE-05 手风琴折叠面板
- **需求**：做一个手风琴组件，包含至少 4 个可折叠的面板。点击面板标题展开内容，再次点击收起。同一时间只允许一个面板展开。
- **古文需求**：作折叠板，列四栏。点其题则展内容，再点则收。同时仅一栏可展。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=responsive, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有多个面板、有展开/收起逻辑、有排他性展开

#### FE-06 星级评分组件
- **需求**：做一个五星评分组件。鼠标悬停时预览评分（星星高亮），点击后确认评分，显示当前已选分数。
- **古文需求**：作五星评分器。悬时预示星亮，点则定分，示已选之数。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=desktop, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有 5 个星星元素、有 hover 交互、有 click 确认、有分数显示

#### FE-07 通知消息条
- **需求**：做一个通知提示组件。支持成功、警告、错误三种类型，每种类型有不同的颜色。通知出现后 3 秒自动消失，也可以手动点关闭按钮消失。
- **古文需求**：作通知条，分成功、警示、误报三类，各异色。现后三秒自隐，亦可手动关之。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=responsive, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有三种类型样式、有自动消失定时器、有关闭按钮

#### FE-08 标签页切换
- **需求**：做一个标签页组件，包含至少 3 个标签。点击标签切换显示对应内容区域，当前激活的标签有高亮样式。
- **古文需求**：作标签页，列三签以上。点签则切示其内容，活签当高亮。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=plain_css, dependencies=no_external, layout=mobile_first, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有多个标签按钮、有内容切换逻辑、有激活态样式

### 中等难度（FE-09 ~ FE-16）

#### FE-09 购物车页面
- **需求**：做一个购物车页面，展示商品列表（至少 3 件），每件商品有名称、单价、数量调节按钮。底部显示总价，总价随数量变化实时更新。有清空购物车按钮。
- **古文需求**：作购物车页，列至少三品，各具名、价、调数之键。底示总价，随量即更。具清空键。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=mobile_first, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有商品列表、有数量加减、有总价计算、有清空功能

#### FE-10 天气仪表盘
- **需求**：做一个天气仪表盘，显示当前城市名称、温度、湿度、风速，以及未来 5 天的天气预报（每天显示日期、天气图标描述、最高/最低温度）。所有数据使用模拟数据。
- **古文需求**：作天气板，示城名、温度、湿度、风速，及未来五日之报（日期、天况、高低温）。数据皆模拟。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=responsive, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有当前天气展示、有 5 天预报列表、有温度/湿度/风速数据

#### FE-11 Markdown 编辑器
- **需求**：做一个左右分栏的 Markdown 编辑器。左侧是文本输入区域，右侧是实时预览区域。支持基本的 Markdown 语法渲染（标题、粗体、斜体、列表、代码块）。不要使用任何第三方 Markdown 解析库，自己用正则实现简单的转换。
- **古文需求**：作左右分栏之 Markdown 编辑器。左为输入，右为实时预览。须渲标题、粗体、斜体、列表、代码块。禁用外库，以正则自为转换。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=plain_css, dependencies=no_external, layout=desktop, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有左右分栏布局、有 textarea 输入、有实时预览渲染、有基本 Markdown 转换

#### FE-12 聊天界面
- **需求**：做一个聊天界面，包含消息气泡列表（区分自己和对方，样式不同）、底部输入框、发送按钮。发送消息后列表自动滚动到底部。用模拟数据预填几条历史消息。
- **古文需求**：作聊天界面，具消息泡列（己方与对方异式）、底部输入栏、发送键。发后自滚至底。预填数条模拟历史。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=mobile_first, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有消息列表、有两种气泡样式、有输入框和发送按钮、有自动滚动

#### FE-13 数据表格
- **需求**：做一个数据表格组件，展示至少 10 行模拟数据（姓名、邮箱、角色、状态）。支持点击列头排序（升序/降序切换）、支持搜索框按姓名筛选、支持分页（每页 5 条）。
- **古文需求**：作数据表，列至少十行模拟数据（名、邮、角色、状态）。可点列头排序，可搜名筛选，可分页（每页五条）。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=desktop, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有表格渲染、有排序功能、有搜索输入框、有分页控件

#### FE-14 图片画廊
- **需求**：做一个图片画廊，以网格布局展示至少 9 张图片（使用 placeholder 图片 URL）。点击图片弹出大图预览弹窗，弹窗中可以关闭。图片使用懒加载（进入视口时才加载）。
- **古文需求**：作图廊，以网格列至少九图（用占位图链接）。点图则弹大图预览，可关之。图须惰加载。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=responsive, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有网格布局、有图片元素、有点击弹窗、有关闭功能、有懒加载属性

#### FE-15 设置面板
- **需求**：做一个设置面板，包含至少 3 个开关切换项（如深色模式、通知、自动保存）、1 个下拉选择器（如语言选择）、1 个保存按钮。点保存后显示"已保存"提示。
- **古文需求**：作设置板，具至少三开关项（如暗色、通知、自存）、一下拉选（如语言）、一存键。存后示"已保存"。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=responsive, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有 toggle 开关、有 select 下拉、有保存按钮、有保存反馈

#### FE-16 多步表单
- **需求**：做一个多步表单（至少 3 步）。第一步填个人信息（姓名、邮箱），第二步填地址信息（城市、邮编），第三步确认并提交。有上一步/下一步按钮，有步骤指示器显示当前在第几步。
- **古文需求**：作三步表单。首步填名与邮，次步填城与邮编，末步确认提交。具上下步键与步骤指示器。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=mobile_first, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有多步状态管理、有步骤指示器、有上一步/下一步导航、有表单字段

### 进阶难度（FE-17 ~ FE-20）

#### FE-17 拖拽排序列表
- **需求**：做一个可拖拽排序的列表，包含至少 5 个项目。用户可以通过拖拽来重新排列项目顺序。不使用任何拖拽库，用原生 HTML5 Drag and Drop API 实现。拖拽过程中要有视觉反馈（如拖拽中的项目半透明）。
- **古文需求**：作可拖拽排序之列表，至少五项。以原生拖放 API 实现排序，禁用外库。拖中当有视觉反馈。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=desktop, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有列表项、有 draggable 属性、有 dragover/drop 事件处理、有状态更新

#### FE-18 实时搜索与高亮
- **需求**：做一个搜索组件，包含搜索输入框和结果列表。列表中有至少 20 条模拟数据（标题+描述）。输入时实时过滤匹配项，并在匹配的文字上加高亮显示。支持防抖（输入后 300ms 才触发过滤）。
- **古文需求**：作搜索组件，含搜索栏与结果列。列中至少廿条模拟数据。输入时即滤即亮匹配文字。须防抖，输后三百毫秒方滤。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=responsive, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有搜索输入框、有结果列表、有高亮标记、有防抖逻辑

#### FE-19 看板任务板
- **需求**：做一个三列看板（待做、进行中、已完成）。每列中有任务卡片，每个卡片显示标题和描述。可以通过按钮将卡片在相邻列之间移动（如从"待做"移到"进行中"）。可以添加新卡片到"待做"列。
- **古文需求**：作三列看板（待做、进行、已毕）。各列有任务卡，示题与描述。可按键移卡于相邻列间。可添新卡于待做列。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=desktop, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有三列布局、有卡片渲染、有列间移动功能、有添加功能

#### FE-20 主题切换仪表盘
- **需求**：做一个带主题切换功能的仪表盘页面。包含顶部导航栏（标题+主题切换按钮）、侧边栏导航（至少 4 个菜单项）、主内容区展示一些统计卡片（4 个数字卡片）。支持亮色/暗色主题切换，切换后所有组件的颜色方案同步变化。
- **古文需求**：作带主题切换之仪表盘。含顶部导航（题与切换键）、侧栏导航（至少四菜单）、主区四统计卡。支持明暗主题切换，切后全部配色同变。
- **约束**：language=TypeScript, framework=React, form=single_file_component, style=tailwind, dependencies=no_external, layout=desktop, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：有导航栏、有侧边栏、有统计卡片、有主题切换功能、有两套配色

---

## 三、Backend 任务（BE-01 ~ BE-20）

**统一技术栈**：Python + FastAPI，单文件模块  
**验证方式**：`uvicorn` 启动 + `httpx` 请求测试（状态码 + 响应结构）

### 基础难度（BE-01 ~ BE-08）

#### BE-01 健康检查接口
- **需求**：做一个 FastAPI 应用，包含一个 GET /health 接口，返回 `{"status": "ok", "timestamp": "<当前时间>"}`。
- **古文需求**：作 FastAPI 应用，具 GET /health 接口，返 status 为 ok 及当前时间。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external(仅fastapi+uvicorn), layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：GET /health 返回 200，响应含 status 和 timestamp 字段

#### BE-02 待办事项 CRUD API
- **需求**：做一个 FastAPI 应用，实现待办事项的完整 CRUD。POST /todos 创建，GET /todos 获取全部，GET /todos/{id} 获取单条，PUT /todos/{id} 更新，DELETE /todos/{id} 删除。数据存在内存列表中即可。
- **古文需求**：作 FastAPI 应用，实现待办之完整增删改查。数据存于内存列表即可。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：5 个端点各返回正确状态码和数据结构

#### BE-03 用户注册接口
- **需求**：做一个 FastAPI 应用，POST /register 接收用户名、邮箱、密码。验证邮箱格式和密码长度（至少 8 位），验证不通过返回 422 和错误信息，通过则返回 201 和用户信息（不含密码）。
- **古文需求**：作 FastAPI 应用，POST /register 收用户名、邮箱、密码。验邮之格式与密之长度（至少八位），不合返 422，合则返 201 及用户信息（不含密码）。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：合法输入返回 201，非法邮箱返回 422，短密码返回 422

#### BE-04 简易计算器 API
- **需求**：做一个 FastAPI 应用，POST /calculate 接收 `{"a": number, "b": number, "op": "add|sub|mul|div"}`，返回计算结果。除以零时返回 400 和错误信息。
- **古文需求**：作 FastAPI 应用，POST /calculate 收二数与运算符，返计算结果。除零则返 400 及误信。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：四种运算正确，除零返回 400

#### BE-05 分页查询接口
- **需求**：做一个 FastAPI 应用，GET /items 支持分页参数 page 和 page_size（默认 page=1, page_size=10）。返回包含 items 列表、total 总数、page 当前页、page_size 每页数量、total_pages 总页数的 JSON。使用模拟的 50 条数据。
- **古文需求**：作 FastAPI 应用，GET /items 支持分页参数。返 items、total、page、page_size、total_pages。以五十条模拟数据。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：分页参数正确处理，边界页码正确，total_pages 计算正确

#### BE-06 短链接生成服务
- **需求**：做一个 FastAPI 应用。POST /shorten 接收 `{"url": "https://..."}` 返回一个 6 位随机短码。GET /{code} 重定向到原始 URL。如果短码不存在返回 404。
- **古文需求**：作 FastAPI 应用。POST /shorten 收原始链接返六位短码。GET /{code} 重定向至原址。码不存则返 404。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：POST 返回短码，GET 重定向（307），无效码返回 404

#### BE-07 JSON 数据验证接口
- **需求**：做一个 FastAPI 应用，POST /validate 接收任意 JSON 对象，检查是否包含 name(字符串)、age(整数且>0)、email(含@) 三个必填字段。全部合法返回 `{"valid": true}`，否则返回 `{"valid": false, "errors": [...]}`。
- **古文需求**：作 FastAPI 应用，POST /validate 收 JSON，验 name(字串)、age(正整数)、email(含@) 三必填字段。皆合返 valid:true，否则返 valid:false 及 errors。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：合法输入返回 valid:true，各字段缺失/类型错误时返回正确的 errors

#### BE-08 简易键值存储 API
- **需求**：做一个 FastAPI 应用，实现内存键值存储。PUT /store/{key} 存值（body 为 `{"value": any}`），GET /store/{key} 取值，DELETE /store/{key} 删值。不存在的 key 返回 404。
- **古文需求**：作 FastAPI 应用，实现内存键值存储。PUT 存值，GET 取值，DELETE 删值。键不存则返 404。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：PUT 存值成功，GET 取值正确，DELETE 删值成功，不存在返回 404

### 中等难度（BE-09 ~ BE-16）

#### BE-09 JWT 认证流程
- **需求**：做一个 FastAPI 应用。POST /login 接收用户名和密码（硬编码一个用户 admin/password123），验证通过返回一个 JWT token。GET /protected 需要在 Authorization header 中带 Bearer token，验证通过返回用户信息，验证失败返回 401。JWT 用 Python 标准库的 hmac+base64 手动实现，不用 PyJWT。
- **古文需求**：作 FastAPI 应用。POST /login 验用户名密码（硬编码 admin/password123），通过则返 JWT token。GET /protected 须带 Bearer token，通过返用户信息，败返 401。以标准库手动实现 JWT。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：正确登录返回 token，带 token 访问 /protected 成功，不带 token 返回 401

#### BE-10 文件信息接口
- **需求**：做一个 FastAPI 应用。POST /upload 接收一个文件上传（multipart/form-data），返回文件名、文件大小（字节）、MIME 类型。不需要真正保存文件，只提取信息。
- **古文需求**：作 FastAPI 应用。POST /upload 收上传文件，返文件名、大小、MIME 类型。不须真存，仅提取信息。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：上传文件后返回正确的文件名、大小、类型

#### BE-11 限流中间件
- **需求**：做一个 FastAPI 应用，实现一个简易限流中间件。GET /api/data 返回模拟数据。同一 IP 在 60 秒内最多请求 10 次，超过后返回 429 Too Many Requests。用内存字典记录。
- **古文需求**：作 FastAPI 应用，加限流中间件。GET /api/data 返模拟数据。同 IP 六十秒内至多十次请求，逾则返 429。以内存字典记录。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：正常请求返回 200，超限返回 429

#### BE-12 多条件搜索接口
- **需求**：做一个 FastAPI 应用，GET /search 支持多个可选查询参数：q(关键词), category(分类), min_price(最低价), max_price(最高价), sort_by(排序字段), order(asc/desc)。在 50 条模拟商品数据中筛选并返回结果。
- **古文需求**：作 FastAPI 应用，GET /search 支持关键词、分类、价格范围、排序等多可选参数。于五十条模拟商品中筛选返结果。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：各筛选参数独立工作，组合筛选正确，排序正确

#### BE-13 批量操作接口
- **需求**：做一个 FastAPI 应用。POST /batch 接收一个操作列表 `{"operations": [{"action": "create|update|delete", "data": {...}}]}`，逐条执行并返回每条操作的结果（成功或失败及原因）。用内存存储，单条失败不影响其他。
- **古文需求**：作 FastAPI 应用。POST /batch 收操作列表，逐条执行增、改、删，返每条结果。以内存存储，单条败不影响他。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：批量操作各自独立，返回每条结果，单条失败不阻塞

#### BE-14 事件日志接口
- **需求**：做一个 FastAPI 应用。POST /events 记录一条事件（type, message, timestamp自动生成）。GET /events 返回全部事件。GET /events?type=error 按类型筛选。GET /events/stats 返回各类型事件的计数统计。
- **古文需求**：作 FastAPI 应用。POST /events 记事件。GET /events 取全部或按类型筛。GET /events/stats 返各类型计数统计。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：创建事件成功，筛选正确，统计计数正确

#### BE-15 数据转换接口
- **需求**：做一个 FastAPI 应用。POST /transform 接收一个 JSON 对象和一组转换规则 `{"data": {...}, "transforms": ["uppercase_keys", "flatten", "remove_nulls"]}`。按顺序执行转换：uppercase_keys 将所有 key 大写，flatten 将嵌套对象拉平（用.连接key），remove_nulls 删除值为 null 的字段。返回转换后的对象。
- **古文需求**：作 FastAPI 应用。POST /transform 收 JSON 对象与转换规则列表，按序执行：大写键名、拉平嵌套（以.连key）、移除空值。返转换后之对象。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：三种转换各自正确，组合应用顺序正确

#### BE-16 环境配置接口
- **需求**：做一个 FastAPI 应用。启动时从环境变量或默认值加载配置（APP_NAME 默认 "MyApp"，DEBUG 默认 "false"，MAX_ITEMS 默认 "100"）。GET /config 返回当前配置。PUT /config 允许在运行时动态修改配置值。POST /config/reset 重置为默认值。
- **古文需求**：作 FastAPI 应用。启动时从环境变量或默认值加载配置。GET /config 返当前配置，PUT /config 动态改之，POST /config/reset 归默认。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：默认配置正确，修改后读取正确，重置后恢复默认

### 进阶难度（BE-17 ~ BE-20）

#### BE-17 WebSocket 聊天室
- **需求**：做一个 FastAPI 应用，实现 WebSocket 聊天室。WS /ws/{username} 连接后可收发消息。一个用户发送的消息应广播给所有其他已连接的用户。用户连接和断开时广播通知。
- **古文需求**：作 FastAPI 应用，实现 WebSocket 聊天室。WS /ws/{username} 连后可收发消息。一人之消息广播于所有他人。连断时均广播通知。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：WebSocket 连接成功，消息广播正确，断连通知正确

#### BE-18 任务队列模拟
- **需求**：做一个 FastAPI 应用，模拟异步任务队列。POST /tasks 提交一个任务（返回 task_id，状态为 pending）。后台用 asyncio 模拟处理（等 2 秒后变为 completed）。GET /tasks/{id} 查询任务状态。GET /tasks 查看所有任务。
- **古文需求**：作 FastAPI 应用，模拟异步任务队列。POST /tasks 提交任务（返 task_id，状态 pending）。后台以 asyncio 模拟处理（二秒后变 completed）。GET 可查单任务或全部。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：提交返回 pending，等待后查询返回 completed

#### BE-19 API 版本管理
- **需求**：做一个 FastAPI 应用，同时提供 v1 和 v2 两个版本的接口。GET /v1/users 返回简化的用户列表（只有 id 和 name）。GET /v2/users 返回完整的用户列表（id, name, email, created_at）。GET /v2/users/{id} 返回单个用户详情（v1 没有这个端点）。两个版本共享同一份模拟数据。
- **古文需求**：作 FastAPI 应用，同时供 v1 与 v2 二版接口。v1 /users 返简化用户列。v2 /users 返完整列，v2 /users/{id} 返单用户详情。二版共享同一模拟数据。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=mock, output=code_only, tests=false, comments=false
- **验证要点**：v1 和 v2 响应结构不同，v2 多一个详情端点，数据一致

#### BE-20 中间件链
- **需求**：做一个 FastAPI 应用，实现三个中间件按顺序执行：(1) 请求日志中间件——记录每个请求的方法、路径、耗时到内存列表；(2) CORS 中间件——手动添加 Access-Control 相关 header；(3) 请求 ID 中间件——给每个请求/响应添加 X-Request-ID header。GET /logs 返回收集到的请求日志。GET /test 是一个普通的测试端点。
- **古文需求**：作 FastAPI 应用，实现三中间件依次执行：请求日志（记法、路径、耗时）、CORS（手加 Access-Control header）、请求 ID（加 X-Request-ID header）。GET /logs 返请求日志，GET /test 为测试端点。
- **约束**：language=Python, framework=FastAPI, form=single_module, style=not_applicable, dependencies=no_external, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：响应包含 X-Request-ID 和 CORS header，/logs 记录了请求信息

---

## 四、Python Script 任务（PY-01 ~ PY-20）

**统一技术栈**：Python 3.12+，仅标准库（除非任务明确指定）  
**验证方式**：`python -m pytest` 跑预写单测

### 基础难度（PY-01 ~ PY-08）

#### PY-01 CSV 解析器
- **需求**：写一个 Python 函数 `parse_csv(text: str) -> list[dict]`，将 CSV 格式文本（第一行为表头）解析为字典列表。处理引号内的逗号（`"Smith, John"` 不应拆分）。仅用标准库。
- **古文需求**：写一 Python 函数 parse_csv，将 CSV 文本（首行为表头）解析为字典列表。须正确处理引号内之逗号。仅用标准库。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：基本解析正确，引号内逗号不拆分，空值处理

#### PY-02 JSON 格式转换器
- **需求**：写一个 Python 函数 `flatten_json(nested: dict, separator: str = ".") -> dict`，将嵌套 JSON 对象拉平为单层字典。例如 `{"a": {"b": 1}}` → `{"a.b": 1}`。支持嵌套列表（`{"a": [1,2]}` → `{"a.0": 1, "a.1": 2}`）。
- **古文需求**：写一函数 flatten_json，将嵌套 JSON 拉平为单层字典，以 separator 连 key。须支持嵌套列表。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：嵌套字典拉平正确，列表索引拉平正确，自定义分隔符有效

#### PY-03 文件批量重命名器
- **需求**：写一个 Python 函数 `generate_rename_plan(filenames: list[str], pattern: str, start: int = 1) -> list[tuple[str, str]]`。输入文件名列表和命名模板（如 "photo_{n:03d}"），返回 (旧名, 新名) 列表。新名保留原始扩展名。不执行实际重命名，只生成计划。
- **古文需求**：写一函数 generate_rename_plan，入文件名列表与命名模板，返旧名新名之列表。新名须保留原扩展名。不执行重命名，仅生成计划。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：编号正确，扩展名保留，模板格式化正确

#### PY-04 正则表达式提取器
- **需求**：写一个 Python 函数 `extract_info(text: str) -> dict`，从给定文本中提取所有邮箱地址、URL、电话号码（中国大陆手机号格式）。返回 `{"emails": [...], "urls": [...], "phones": [...]}`。
- **古文需求**：写一函数 extract_info，从文本中提取所有邮箱、URL、手机号（中国大陆格式），返三类列表。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：邮箱提取正确，URL 提取正确，手机号提取正确

#### PY-05 文本统计器
- **需求**：写一个 Python 函数 `text_stats(text: str) -> dict`，返回统计信息：字符数、单词数、句子数、段落数、最常见的 5 个单词（忽略大小写，排除常见停用词 the/a/an/is/are/was/were/in/on/at/to/for）。
- **古文需求**：写一函数 text_stats，返文本统计：字符数、词数、句数、段数、最常见五词（忽略大小写，排除常见停用词）。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：各计数正确，停用词排除正确，词频排序正确

#### PY-06 简易密码生成器
- **需求**：写一个 Python 函数 `generate_password(length: int = 16, uppercase: bool = True, digits: bool = True, special: bool = True) -> str`。生成随机密码，根据参数决定是否包含大写字母、数字、特殊字符。密码必须至少包含每种被要求的字符类型各一个。
- **古文需求**：写一函数 generate_password，生成随机密码。按参数决定是否含大写、数字、特殊字符。每类要求之字符至少含一。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：长度正确，包含要求的字符类型，随机性

#### PY-07 日期计算器
- **需求**：写一个 Python 函数 `date_calc(date_str: str, operation: str) -> str`。输入日期（YYYY-MM-DD 格式）和操作字符串（如 "+3d" 加3天，"-2w" 减2周，"+1m" 加1月，"-1y" 减1年），返回计算后的日期字符串。
- **古文需求**：写一函数 date_calc，入日期字符串与操作符（如 +3d 加三天，-2w 减二周，+1m 加一月，-1y 减一年），返计算后之日期。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：天/周/月/年计算正确，跨月/跨年正确

#### PY-08 矩阵运算库
- **需求**：写一组 Python 函数实现基本矩阵运算（不用 numpy）：`matrix_add(a, b)` 矩阵加法，`matrix_multiply(a, b)` 矩阵乘法，`matrix_transpose(a)` 转置，`matrix_determinant(a)` 行列式（支持 2×2 和 3×3）。矩阵用 list[list[float]] 表示。
- **古文需求**：写一组函数实现矩阵运算（不用 numpy）：加法、乘法、转置、行列式（支持二阶与三阶）。以嵌套列表表示矩阵。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：加法正确，乘法维度匹配正确，转置正确，行列式计算正确

### 中等难度（PY-09 ~ PY-16）

#### PY-09 CLI 参数解析工具
- **需求**：写一个 Python 函数 `parse_args(args: list[str], schema: dict) -> dict`。schema 定义参数名、类型、默认值、是否必填。例如 `{"--name": {"type": "str", "required": True}, "--count": {"type": "int", "default": 1}}`。支持 `--key value` 和 `--key=value` 两种写法。不使用 argparse，自己实现。
- **古文需求**：写一函数 parse_args，按 schema 解析命令行参数列表。支持 --key value 与 --key=value 两式。不用 argparse，自行实现。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：两种格式解析正确，类型转换正确，必填检查正确，默认值正确

#### PY-10 日志分析器
- **需求**：写一个 Python 函数 `analyze_logs(log_text: str) -> dict`。输入是多行日志文本，每行格式为 `[TIMESTAMP] [LEVEL] message`（如 `[2026-03-31 10:00:00] [ERROR] Connection failed`）。返回：总行数、各级别（INFO/WARN/ERROR）计数、ERROR 级别的全部消息列表、最早和最晚的时间戳。
- **古文需求**：写一函数 analyze_logs，入多行日志文本，返总行数、各级别计数、ERROR 消息列表、最早与最晚时间戳。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：各级别计数正确，ERROR 消息提取正确，时间范围正确

#### PY-11 简易 HTTP 客户端
- **需求**：写一个 Python 类 `SimpleHTTPClient`，使用标准库 `urllib.request` 封装常用操作：`get(url)` 发 GET 请求返回响应文本，`post(url, data)` 发 POST 请求（JSON body），`download(url, filepath)` 下载文件到指定路径。所有方法返回 `{"status": int, "body": str/None, "headers": dict}`。处理常见异常（超时、404等）。
- **古文需求**：写一 Python 类 SimpleHTTPClient，以标准库封装 get、post、download 三法。返状态码、响应体、头信息。须处理常见异常。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：GET/POST 方法签名正确，异常处理存在，返回结构正确

#### PY-12 配置文件合并器
- **需求**：写一个 Python 函数 `merge_configs(base: dict, override: dict, strategy: str = "deep") -> dict`。支持两种合并策略：`"shallow"` 只覆盖顶层 key，`"deep"` 递归合并嵌套字典。列表类型的值用追加方式合并（不去重）。
- **古文需求**：写一函数 merge_configs，以 base 与 override 二字典合并。支持浅合并与深合并二策。列表值以追加方式合并。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：浅合并只覆盖顶层，深合并递归正确，列表追加正确

#### PY-13 Markdown 转 HTML
- **需求**：写一个 Python 函数 `md_to_html(markdown: str) -> str`，将 Markdown 文本转换为 HTML。支持：标题（# ~ ###）、粗体（**text**）、斜体（*text*）、无序列表（- item）、有序列表（1. item）、行内代码（\`code\`）、代码块（\`\`\`code\`\`\`）、链接（[text](url)）。不使用任何第三方库。
- **古文需求**：写一函数 md_to_html，将 Markdown 转 HTML。支持标题、粗体、斜体、有序与无序列表、行内代码、代码块、链接。不用外库。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：各 Markdown 元素转换正确

#### PY-14 数据管道处理器
- **需求**：写一个 Python 类 `Pipeline`。支持链式调用：`Pipeline(data).filter(fn).map(fn).sort(key).limit(n).execute()`。data 是字典列表。filter 按条件过滤，map 对每项做变换，sort 排序，limit 取前 N 条，execute 返回最终结果。
- **古文需求**：写一 Python 类 Pipeline，支持链式调用：filter、map、sort、limit、execute。data 为字典列表。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：链式调用正确，各操作独立正确，组合顺序正确

#### PY-15 简易模板引擎
- **需求**：写一个 Python 函数 `render_template(template: str, context: dict) -> str`。支持变量替换 `{{name}}`、条件块 `{% if condition %}...{% endif %}`、循环块 `{% for item in list %}...{% endfor %}`。变量支持点号访问 `{{user.name}}`。
- **古文需求**：写一函数 render_template，支持变量替换 {{name}}、条件块 if/endif、循环块 for/endfor。变量支持点号访问。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：变量替换正确，条件判断正确，循环渲染正确，点号访问正确

#### PY-16 事件发布订阅系统
- **需求**：写一个 Python 类 `EventBus`。支持 `on(event, callback)` 订阅事件，`off(event, callback)` 取消订阅，`emit(event, *args)` 触发事件（调用所有订阅者），`once(event, callback)` 只触发一次就自动取消。
- **古文需求**：写一 Python 类 EventBus，支持 on 订阅、off 退订、emit 触发、once 仅触发一次即退。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：订阅和触发正确，取消订阅有效，once 只触发一次

### 进阶难度（PY-17 ~ PY-20）

#### PY-17 并发下载管理器
- **需求**：写一个 Python 类 `DownloadManager`，使用 `concurrent.futures.ThreadPoolExecutor` 实现并发下载。`add(url, filepath)` 添加下载任务，`start(max_workers=4)` 开始并发下载，`status()` 返回每个任务的状态（pending/downloading/completed/failed）。用标准库 `urllib.request` 做实际下载。
- **古文需求**：写一 Python 类 DownloadManager，以 ThreadPoolExecutor 实现并发下载。支持 add 添加任务、start 开始下载、status 查各任务状态。以标准库下载。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：任务添加正确，并发执行正确，状态跟踪正确

#### PY-18 DAG 任务调度器
- **需求**：写一个 Python 类 `DAGScheduler`。`add_task(name, fn, depends_on=[])` 添加任务及其依赖。`run()` 按拓扑序执行所有任务（依赖全完成后才执行当前任务）。检测循环依赖并抛出异常。返回每个任务的执行结果和执行顺序。
- **古文需求**：写一 Python 类 DAGScheduler。add_task 添加任务及其依赖，run 按拓扑序执行。须检测循环依赖并抛异常。返各任务结果与执行顺序。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：拓扑排序正确，依赖执行顺序正确，循环检测正确

#### PY-19 简易正则引擎
- **需求**：写一个 Python 函数 `simple_match(pattern: str, text: str) -> bool`，实现一个极简的正则匹配引擎（不用 re 模块）。支持：`.` 匹配任意单字符，`*` 表示前一个字符重复 0 次或多次，`^` 匹配开头，`$` 匹配结尾。
- **古文需求**：写一函数 simple_match，实现极简正则匹配（不用 re 模块）。支持 . 匹配任意单字符、* 重复零次或多次、^ 匹配开头、$ 匹配结尾。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：各通配符功能正确，组合使用正确

#### PY-20 AST 代码检查器
- **需求**：写一个 Python 函数 `check_code(source: str) -> list[dict]`，使用标准库 `ast` 模块分析 Python 源代码，检查并报告以下问题：(1) 函数超过 20 行；(2) 函数参数超过 5 个；(3) 嵌套深度超过 3 层；(4) 使用了 eval() 或 exec()。每个问题返回 `{"line": int, "issue": str, "severity": "warning|error"}`。
- **古文需求**：写一函数 check_code，以标准库 ast 模块分析 Python 源码，检查并报告：函数超二十行、参数超五个、嵌套超三层、使用 eval/exec。每问题返行号、描述与严重度。
- **约束**：language=Python, framework=None, form=function_library, style=not_applicable, dependencies=stdlib_only, layout=not_applicable, data=not_applicable, output=code_only, tests=false, comments=false
- **验证要点**：各检查项检出正确，行号正确，严重度正确

---

## 五、Pilot 子集（12 个任务）

Phase B 先跑以下 12 个任务验证 pipeline：

| 类型 | 任务 | 难度 |
|------|------|------|
| Frontend | FE-01 登录表单 | 基础 |
| Frontend | FE-09 购物车页面 | 中等 |
| Frontend | FE-13 数据表格 | 中等 |
| Frontend | FE-17 拖拽排序列表 | 进阶 |
| Backend | BE-02 待办事项 CRUD | 基础 |
| Backend | BE-05 分页查询 | 基础 |
| Backend | BE-09 JWT 认证 | 中等 |
| Backend | BE-17 WebSocket 聊天 | 进阶 |
| Python | PY-01 CSV 解析器 | 基础 |
| Python | PY-05 文本统计器 | 基础 |
| Python | PY-14 数据管道处理器 | 中等 |
| Python | PY-18 DAG 任务调度器 | 进阶 |

---

*任务定义完成时间：2026-03-31 12:01*
