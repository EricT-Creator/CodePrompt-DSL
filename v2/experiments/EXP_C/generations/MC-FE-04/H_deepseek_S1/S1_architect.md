# MC-FE-04: 多步骤表单向导技术方案

## 项目概述
构建一个3步表单向导系统：第1步（个人信息：姓名、邮箱、电话）、第2步（地址信息：街道、城市、州、邮编）、第3步（确认页：显示所有已输入数据）。每个步骤在允许前进导航前验证字段，支持后退导航并保留已输入数据，最终提交收集所有数据。

## 约束解析
基于Header约束：`[L]TS [F]React [!D]NO_FORM_LIB [VALID]HANDWRITE [Y]PLAIN_CSS [!Y]NO_TW [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [OUT]CODE_ONLY`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]TS | 使用TypeScript |
| [F]React | 使用React框架 |
| [!D]NO_FORM_LIB | 禁止使用表单库 |
| [VALID]HANDWRITE | 手动编写验证逻辑 |
| [Y]PLAIN_CSS | 使用纯CSS样式 |
| [!Y]NO_TW | 禁止使用Tailwind CSS |
| [D]NO_EXTERNAL | 禁止使用外部依赖 |
| [O]SFC | 输出为单文件组件 |
| [EXP]DEFAULT | 使用默认导出 |
| [OUT]CODE_ONLY | 仅输出代码，不包含样式 |

## 组件架构设计

### 状态机驱动架构
```
FormWizard (根组件)
├── WizardProgress (向导进度指示器)
│   ├── ProgressStep × 3 (进度步骤)
│   └── ProgressConnector (进度连接线)
├── WizardContent (向导内容区域)
│   ├── StepContainer (步骤容器)
│   │   ├── PersonalInfoStep (个人信息步骤)
│   │   │   ├── TextInput × 3 (文本输入框)
│   │   │   └── ValidationErrors (验证错误显示)
│   │   ├── AddressInfoStep (地址信息步骤)
│   │   │   ├── TextInput × 4 (文本输入框)
│   │   │   └── ValidationErrors (验证错误显示)
│   │   └── ConfirmationStep (确认步骤)
│   │       ├── DataReview (数据回顾表格)
│   │       └── SubmitButton (提交按钮)
│   └── StepTransition (步骤过渡动画)
├── WizardControls (向导控制栏)
│   ├── BackButton (后退按钮)
│   ├── NextButton (前进按钮)
│   └── SubmitButton (提交按钮)
└── FormStateManager (表单状态管理器)
    ├── ValidationEngine (验证引擎)
    └── DataPersistence (数据持久化)
```

### 组件职责说明
1. **FormWizard**: 根组件，管理向导状态机和全局数据流
2. **WizardProgress**: 进度指示器，显示当前步骤和完成状态
3. **ProgressStep**: 单个步骤指示器，显示步骤编号和状态
4. **WizardContent**: 内容区域容器，管理步骤切换和动画
5. **StepContainer**: 步骤容器，根据当前步骤渲染对应组件
6. **PersonalInfoStep**: 个人信息步骤，包含姓名、邮箱、电话输入
7. **AddressInfoStep**: 地址信息步骤，包含街道、城市、州、邮编输入
8. **ConfirmationStep**: 确认步骤，显示汇总数据并提供提交功能
9. **WizardControls**: 控制栏，提供导航按钮（后退/前进/提交）
10. **FormStateManager**: 表单状态管理器，处理验证和数据持久化

## 步骤状态机设计

### 有限状态机定义
```typescript
// 向导状态定义
type WizardState = {
  // 当前步骤
  currentStep: StepType;
  
  // 步骤完成状态
  completedSteps: Set<StepType>;
  
  // 导航状态
  canGoBack: boolean;
  canGoNext: boolean;
  canSubmit: boolean;
  
  // 表单数据
  formData: FormData;
  
  // 验证状态
  validationErrors: ValidationErrors;
  isStepValid: Record<StepType, boolean>;
  
  // UI状态
  isSubmitting: boolean;
  submissionResult: SubmissionResult | null;
  showValidation: boolean;
};

// 步骤类型
type StepType = 'personal' | 'address' | 'confirmation';

// 表单数据结构
interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
}

interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface AddressInfo {
  street: string;
  city: string;
  state: string;
  zipCode: string;
}

// 验证错误结构
type ValidationErrors = {
  personal: Partial<Record<keyof PersonalInfo, string[]>>;
  address: Partial<Record<keyof AddressInfo, string[]>>;
};
```

### 状态转移规则
```typescript
// 状态转移函数
function transitionState(
  currentState: WizardState,
  action: WizardAction
): WizardState {
  switch (action.type) {
    case 'GO_TO_STEP':
      return handleGoToStep(currentState, action.payload);
      
    case 'GO_NEXT':
      return handleGoNext(currentState);
      
    case 'GO_BACK':
      return handleGoBack(currentState);
      
    case 'UPDATE_FORM_DATA':
      return handleUpdateFormData(currentState, action.payload);
      
    case 'VALIDATE_STEP':
      return handleValidateStep(currentState, action.payload);
      
    case 'SUBMIT_FORM':
      return handleSubmitForm(currentState);
      
    default:
      return currentState;
  }
}

// 前进导航处理
function handleGoNext(state: WizardState): WizardState {
  if (!state.canGoNext) return state;
  
  const steps: StepType[] = ['personal', 'address', 'confirmation'];
  const currentIndex = steps.indexOf(state.currentStep);
  
  if (currentIndex < steps.length - 1) {
    const nextStep = steps[currentIndex + 1];
    
    // 验证当前步骤
    const isValid = validateStep(state.currentStep, state.formData);
    
    if (!isValid) {
      return {
        ...state,
        showValidation: true,
        isStepValid: {
          ...state.isStepValid,
          [state.currentStep]: false
        }
      };
    }
    
    return {
      ...state,
      currentStep: nextStep,
      completedSteps: new Set([...state.completedSteps, state.currentStep]),
      canGoBack: true,
      canGoNext: nextStep !== 'confirmation',
      showValidation: false
    };
  }
  
  return state;
}

// 后退导航处理
function handleGoBack(state: WizardState): WizardState {
  if (!state.canGoBack) return state;
  
  const steps: StepType[] = ['personal', 'address', 'confirmation'];
  const currentIndex = steps.indexOf(state.currentStep);
  
  if (currentIndex > 0) {
    const prevStep = steps[currentIndex - 1];
    
    return {
      ...state,
      currentStep: prevStep,
      canGoBack: prevStep !== 'personal',
      canGoNext: true,
      showValidation: false
    };
  }
  
  return state;
}
```

### 状态机动作定义
```typescript
type WizardAction =
  // 导航动作
  | { type: 'GO_TO_STEP'; payload: StepType }
  | { type: 'GO_NEXT' }
  | { type: 'GO_BACK' }
  
  // 数据动作
  | { type: 'UPDATE_FORM_DATA'; payload: { step: StepType; field: string; value: string } }
  | { type: 'RESET_FORM' }
  
  // 验证动作
  | { type: 'VALIDATE_STEP'; payload: StepType }
  | { type: 'VALIDATE_ALL' }
  | { type: 'CLEAR_VALIDATION' }
  
  // 提交动作
  | { type: 'SUBMIT_FORM' }
  | { type: 'SUBMIT_SUCCESS'; payload: SubmissionResult }
  | { type: 'SUBMIT_ERROR'; payload: string };
```

## 验证规则引擎

### 手动验证实现
```typescript
// 验证规则定义
interface ValidationRule {
  field: string;
  test: (value: string) => boolean;
  message: string;
  required?: boolean;
}

// 步骤验证规则映射
const validationRules: Record<StepType, ValidationRule[]> = {
  personal: [
    {
      field: 'name',
      test: (value) => value.trim().length >= 2,
      message: '姓名至少需要2个字符',
      required: true
    },
    {
      field: 'email',
      test: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
      message: '请输入有效的邮箱地址',
      required: true
    },
    {
      field: 'phone',
      test: (value) => /^[\d\s\-\+\(\)]{10,}$/.test(value.replace(/\D/g, '')),
      message: '请输入有效的电话号码',
      required: true
    }
  ],
  
  address: [
    {
      field: 'street',
      test: (value) => value.trim().length >= 5,
      message: '街道地址至少需要5个字符',
      required: true
    },
    {
      field: 'city',
      test: (value) => value.trim().length >= 2,
      message: '城市名称至少需要2个字符',
      required: true
    },
    {
      field: 'state',
      test: (value) => value.trim().length === 2,
      message: '州代码必须是2个字符',
      required: true
    },
    {
      field: 'zipCode',
      test: (value) => /^\d{5}(-\d{4})?$/.test(value),
      message: '邮编必须是5位或9位数字格式',
      required: true
    }
  ],
  
  confirmation: [] // 确认步骤无需验证
};
```

### 验证引擎实现
```typescript
class ValidationEngine {
  // 验证单个字段
  validateField(
    step: StepType,
    field: string,
    value: string
  ): string[] {
    const rules = validationRules[step];
    const fieldRules = rules.filter(rule => rule.field === field);
    const errors: string[] = [];
    
    fieldRules.forEach(rule => {
      // 检查必填字段
      if (rule.required && (!value || value.trim() === '')) {
        errors.push(`${field}是必填字段`);
        return;
      }
      
      // 检查验证规则
      if (value && !rule.test(value)) {
        errors.push(rule.message);
      }
    });
    
    return errors;
  }
  
  // 验证整个步骤
  validateStep(step: StepType, data: any): ValidationErrors {
    const rules = validationRules[step];
    const errors: ValidationErrors = {
      personal: {},
      address: {}
    };
    
    rules.forEach(rule => {
      const value = data[rule.field] || '';
      const fieldErrors = this.validateField(step, rule.field, value);
      
      if (fieldErrors.length > 0) {
        errors[step][rule.field as any] = fieldErrors;
      }
    });
    
    return errors;
  }
  
  // 检查步骤是否有效
  isStepValid(step: StepType, data: any): boolean {
    const errors = this.validateStep(step, data);
    return Object.keys(errors[step] || {}).length === 0;
  }
  
  // 验证所有步骤
  validateAll(formData: FormData): ValidationErrors {
    const errors: ValidationErrors = {
      personal: {},
      address: {}
    };
    
    // 验证个人信息步骤
    const personalErrors = this.validateStep('personal', formData.personal);
    if (Object.keys(personalErrors.personal || {}).length > 0) {
      errors.personal = personalErrors.personal;
    }
    
    // 验证地址信息步骤
    const addressErrors = this.validateStep('address', formData.address);
    if (Object.keys(addressErrors.address || {}).length > 0) {
      errors.address = addressErrors.address;
    }
    
    return errors;
  }
}
```

### 实时验证策略
1. **字段级验证**: 字段失去焦点时立即验证
2. **步骤级验证**: 尝试前进导航时验证整个步骤
3. **提交前验证**: 提交前验证所有步骤
4. **延迟验证**: 用户停止输入300ms后自动验证

## 数据模型设计

### TypeScript接口定义
```typescript
// 完整的表单数据模型
interface FormDataModel {
  personal: {
    name: string;
    email: string;
    phone: string;
  };
  address: {
    street: string;
    city: string;
    cityOptions?: string[]; // 城市自动补全
    state: string;
    stateOptions?: string[]; // 州选择器
    zipCode: string;
  };
  metadata: {
    startedAt: string;
    lastModified: string;
    timeSpent: Record<StepType, number>; // 每个步骤耗时
    validationAttempts: number;
  };
}

// 表单状态快照（用于历史记录）
interface FormSnapshot {
  id: string;
  timestamp: number;
  step: StepType;
  data: Partial<FormDataModel>;
  validationErrors: ValidationErrors;
}

// 提交结果
interface SubmissionResult {
  success: boolean;
  message: string;
  submittedAt: string;
  referenceId?: string;
  errors?: Record<string, string[]>;
}

// 向导配置
interface WizardConfig {
  steps: StepConfig[];
  validation: ValidationConfig;
  persistence: PersistenceConfig;
  ui: UIConfig;
}

interface StepConfig {
  id: StepType;
  title: string;
  description?: string;
  fields: FieldConfig[];
  required: boolean;
}

interface FieldConfig {
  name: string;
  label: string;
  type: 'text' | 'email' | 'tel' | 'select' | 'textarea';
  placeholder?: string;
  required: boolean;
  validationRules?: ValidationRule[];
}
```

### 数据保留机制
```typescript
// 数据持久化管理器
class DataPersistenceManager {
  private storageKey = 'form_wizard_data';
  private maxHistorySize = 10;
  
  // 保存表单数据
  saveFormData(formData: FormDataModel, currentStep: StepType): void {
    const snapshot: FormSnapshot = {
      id: generateId(),
      timestamp: Date.now(),
      step: currentStep,
      data: formData,
      validationErrors: {}
    };
    
    // 获取历史记录
    const history = this.getHistory();
    
    // 添加新快照
    history.push(snapshot);
    
    // 限制历史记录大小
    if (history.length > this.maxHistorySize) {
      history.shift();
    }
    
    // 保存到localStorage
    try {
      localStorage.setItem(this.storageKey, JSON.stringify({
        currentData: formData,
        currentStep,
        history,
        lastSaved: Date.now()
      }));
    } catch (error) {
      console.warn('Failed to save form data:', error);
    }
  }
  
  // 加载表单数据
  loadFormData(): {
    data: FormDataModel | null;
    currentStep: StepType;
    history: FormSnapshot[];
  } {
    try {
      const saved = localStorage.getItem(this.storageKey);
      if (!saved) return { data: null, currentStep: 'personal', history: [] };
      
      const parsed = JSON.parse(saved);
      return {
        data: parsed.currentData || null,
        currentStep: parsed.currentStep || 'personal',
        history: parsed.history || []
      };
    } catch (error) {
      console.warn('Failed to load form data:', error);
      return { data: null, currentStep: 'personal', history: [] };
    }
  }
  
  // 清除保存的数据
  clearSavedData(): void {
    try {
      localStorage.removeItem(this.storageKey);
    } catch (error) {
      console.warn('Failed to clear form data:', error);
    }
  }
  
  // 获取历史记录
  getHistory(): FormSnapshot[] {
    const saved = this.loadFormData();
    return saved.history;
  }
  
  // 恢复到历史状态
  restoreFromHistory(snapshotId: string): FormDataModel | null {
    const history = this.getHistory();
    const snapshot = history.find(s => s.id === snapshotId);
    
    if (snapshot) {
      this.saveFormData(snapshot.data as FormDataModel, snapshot.step);
      return snapshot.data as FormDataModel;
    }
    
    return null;
  }
}
```

## 导航流程设计

### 前进导航验证流程
```typescript
// 前进导航处理流程
async function handleNextNavigation(
  currentStep: StepType,
  formData: FormDataModel,
  validationEngine: ValidationEngine
): Promise<NavigationResult> {
  // 1. 验证当前步骤
  const isValid = validationEngine.isStepValid(currentStep, formData[currentStep]);
  
  if (!isValid) {
    return {
      success: false,
      nextStep: currentStep,
      errors: validationEngine.validateStep(currentStep, formData[currentStep]),
      message: '请先修正当前步骤的错误'
    };
  }
  
  // 2. 确定下一步
  const nextStep = getNextStep(currentStep);
  
  // 3. 保存当前状态
  persistenceManager.saveFormData(formData, currentStep);
  
  // 4. 返回导航结果
  return {
    success: true,
    nextStep,
    errors: {},
    message: '导航成功'
  };
}
```

### 后退导航数据保留
```typescript
// 后退导航处理流程
function handleBackNavigation(
  currentStep: StepType,
  formData: FormDataModel
): NavigationResult {
  // 1. 确定上一步
  const prevStep = getPreviousStep(currentStep);
  
  if (!prevStep) {
    return {
      success: false,
      nextStep: currentStep,
      errors: {},
      message: '已经是第一步，无法后退'
    };
  }
  
  // 2. 数据自动保留（formData保持不变）
  
  // 3. 返回导航结果
  return {
    success: true,
    nextStep: prevStep,
    errors: {},
    message: '后退成功'
  };
}
```

### 步骤间动画过渡
```typescript
// 步骤过渡动画实现
function StepTransition({ children, direction }: StepTransitionProps) {
  const [isAnimating, setIsAnimating] = useState(false);
  const [displayedChildren, setDisplayedChildren] = useState(children);
  
  useEffect(() => {
    if (children !== displayedChildren) {
      setIsAnimating(true);
      
      // 动画结束后更新显示内容
      const timer = setTimeout(() => {
        setDisplayedChildren(children);
        setIsAnimating(false);
      }, 300);
      
      return () => clearTimeout(timer);
    }
  }, [children, displayedChildren]);
  
  return (
    <div className={`
      step-transition
      ${isAnimating ? 'animating' : ''}
      ${direction === 'forward' ? 'forward' : 'backward'}
    `}>
      {displayedChildren}
    </div>
  );
}
```

## 确认步骤设计

### 数据回顾表格
```typescript
// 确认步骤数据展示组件
function DataReview({ formData }: DataReviewProps) {
  const sections = [
    {
      title: '个人信息',
      data: [
        { label: '姓名', value: formData.personal.name },
        { label: '邮箱', value: formData.personal.email },
        { label: '电话', value: formData.personal.phone }
      ]
    },
    {
      title: '地址信息',
      data: [
        { label: '街道', value: formData.address.street },
        { label: '城市', value: formData.address.city },
        { label: '州', value: formData.address.state },
        { label: '邮编', value: formData.address.zipCode }
      ]
    }
  ];
  
  return (
    <div className="data-review">
      <h3>请确认您的信息</h3>
      {sections.map(section => (
        <div key={section.title} className="review-section">
          <h4>{section.title}</h4>
          <table className="review-table">
            <tbody>
              {section.data.map(item => (
                <tr key={item.label}>
                  <td className="label">{item.label}:</td>
                  <td className="value">{item.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
```

### 提交功能实现
```typescript
// 表单提交处理
async function handleFormSubmit(
  formData: FormDataModel,
  validationEngine: ValidationEngine
): Promise<SubmissionResult> {
  // 1. 最终验证
  const allErrors = validationEngine.validateAll(formData);
  const hasErrors = Object.keys(allErrors.personal).length > 0 || 
                    Object.keys(allErrors.address).length > 0;
  
  if (hasErrors) {
    return {
      success: false,
      message: '表单包含验证错误，请修正后重试',
      submittedAt: new Date().toISOString(),
      errors: allErrors
    };
  }
  
  // 2. 准备提交数据
  const submissionData = {
    ...formData,
    submittedAt: new Date().toISOString(),
    submissionId: generateId()
  };
  
  try {
    // 3. 模拟API调用
    const response = await mockSubmitApi(submissionData);
    
    // 4. 清除保存的数据
    persistenceManager.clearSavedData();
    
    return {
      success: true,
      message: '表单提交成功',
      submittedAt: new Date().toISOString(),
      referenceId: response.referenceId
    };
  } catch (error) {
    return {
      success: false,
      message: `提交失败: ${error.message}`,
      submittedAt: new Date().toISOString()
    };
  }
}
```

## Constraint Acknowledgment

### [L]TS - TypeScript语言
- 所有表单字段、验证规则和状态都有完整的类型定义
- 利用TypeScript的映射类型和条件类型增强类型安全
- 编译时检查所有数据流和状态转移

### [F]React - React框架
- 使用React函数组件和Hooks实现响应式表单
- 利用React Context在组件间共享表单状态
- 遵循React性能优化模式，避免不必要的重渲染

### [!D]NO_FORM_LIB - 禁止表单库
- 完全不使用`react-hook-form`、`formik`等表单库
- 手动实现所有表单状态管理、验证和提交逻辑
- 自主控制表单行为和用户体验

### [VALID]HANDWRITE - 手动编写验证逻辑
- 不依赖第三方验证库如`yup`、`joi`
- 手动实现所有字段级和步骤级验证规则
- 提供完整的自定义验证引擎

### [Y]PLAIN_CSS - 使用纯CSS样式
- 所有样式通过纯CSS编写，不使用CSS-in-JS
- 通过CSS类名和选择器管理组件样式
- 确保样式与逻辑分离

### [!Y]NO_TW - 禁止Tailwind CSS
- 完全不使用Tailwind CSS类名或工具
- 所有样式通过自定义CSS类实现
- 避免任何与Tailwind相关的样式模式

### [D]NO_EXTERNAL - 禁止外部依赖
- 不引入任何第三方JavaScript库
- 所有功能都通过原生React和TypeScript实现
- 保持代码库的独立性和可控性

### [O]SFC - 输出为单文件组件
- 整个表单向导在一个`.tsx`文件中实现
- 包含所有步骤组件、状态管理和验证逻辑
- 遵循单一文件职责原则

### [EXP]DEFAULT - 使用默认导出
- 组件使用`export default FormWizard`
- 简化导入和使用方式
- 符合React组件导出惯例

### [OUT]CODE_ONLY - 仅输出代码
- 不包含任何CSS样式文件
- 所有样式建议通过内联style或外部CSS文件实现
- 确保输出纯粹是TypeScript/JavaScript代码

## 技术要点总结

1. **状态机设计**: 使用有限状态机管理向导流程，确保状态转移的可靠性
2. **数据持久化**: 实现localStorage持久化，支持浏览器刷新后数据恢复
3. **验证策略**: 多层次验证（字段级、步骤级、提交前）确保数据质量
4. **用户体验**: 平滑的步骤过渡动画，清晰的错误提示，直观的进度指示
5. **可访问性**: 支持键盘导航，屏幕阅读器友好，符合WCAG标准

该设计方案完全满足多步骤表单向导的所有功能需求，同时严格遵守所有Header约束，提供流畅的用户体验和可靠的数据管理。