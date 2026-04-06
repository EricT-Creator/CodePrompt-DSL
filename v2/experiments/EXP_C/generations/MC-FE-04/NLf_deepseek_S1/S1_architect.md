# MC-FE-04: 3步表单向导技术方案

## 1. 步骤状态机设计

### 1.1 状态定义
```typescript
type WizardStep = 1 | 2 | 3;

interface WizardState {
  currentStep: WizardStep;
  steps: {
    [key in WizardStep]: {
      completed: boolean;
      valid: boolean;
      touched: boolean;
    }
  };
  navigation: {
    canGoNext: boolean;
    canGoBack: boolean;
    canSubmit: boolean;
  };
}
```

### 1.2 状态转换
```typescript
// 状态转换规则
const stateTransitions = {
  // 前进条件：当前步骤验证通过
  NEXT: (state: WizardState): WizardState => ({
    ...state,
    currentStep: Math.min(state.currentStep + 1, 3) as WizardStep,
    steps: {
      ...state.steps,
      [state.currentStep]: { ...state.steps[state.currentStep], completed: true }
    }
  }),
  
  // 后退条件：总是允许（除了第一步）
  PREV: (state: WizardState): WizardState => ({
    ...state,
    currentStep: Math.max(state.currentStep - 1, 1) as WizardStep
  }),
  
  // 提交条件：所有步骤完成且验证通过
  SUBMIT: (state: WizardState): WizardState => ({
    ...state,
    navigation: { ...state.navigation, isSubmitting: true }
  })
};
```

### 1.3 状态机实现
- **有限状态机模式**: 使用纯函数实现状态转换
- **状态验证**: 每次转换前验证条件
- **历史跟踪**: 记录状态转换历史
- **回滚支持**: 支持状态回滚到之前步骤

## 2. 每步验证规则

### 2.1 步骤1：个人信息验证
```typescript
interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

const step1Validations = {
  name: {
    required: true,
    minLength: 2,
    maxLength: 50,
    pattern: /^[a-zA-Z\s]+$/, // 只允许字母和空格
    message: '姓名必须为2-50个字母字符'
  },
  email: {
    required: true,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    message: '请输入有效的电子邮件地址'
  },
  phone: {
    required: true,
    pattern: /^[\d\s\-\+\(\)]{10,20}$/,
    message: '请输入有效的电话号码'
  }
};
```

### 2.2 步骤2：地址信息验证
```typescript
interface AddressInfo {
  street: string;
  city: string;
  state: string;
  zip: string;
}

const step2Validations = {
  street: {
    required: true,
    minLength: 5,
    maxLength: 100,
    message: '街道地址必须为5-100个字符'
  },
  city: {
    required: true,
    minLength: 2,
    maxLength: 50,
    pattern: /^[a-zA-Z\s\-]+$/,
    message: '城市名称必须为2-50个字母字符'
  },
  state: {
    required: true,
    pattern: /^[A-Z]{2}$/, // 美国州缩写
    message: '请输入有效的州缩写（如CA、NY）'
  },
  zip: {
    required: true,
    pattern: /^\d{5}(-\d{4})?$/, // 美国邮政编码
    message: '请输入有效的邮政编码（如12345或12345-6789）'
  }
};
```

### 2.3 步骤3：确认页面
- **只读显示**: 显示前两步收集的所有数据
- **数据格式化**: 格式化显示数据（如电话号码格式）
- **编辑链接**: 提供返回编辑的链接
- **最终确认**: 用户确认数据正确性

## 3. 数据模型

### 3.1 表单数据结构
```typescript
interface FormData {
  // 步骤1数据
  personalInfo: PersonalInfo;
  
  // 步骤2数据
  addressInfo: AddressInfo;
  
  // 元数据
  metadata: {
    submittedAt: Date | null;
    submissionId: string | null;
    validationErrors: ValidationErrors;
  };
}

interface ValidationErrors {
  step1: Record<keyof PersonalInfo, string[]>;
  step2: Record<keyof AddressInfo, string[]>;
  global: string[];
}
```

### 3.2 验证状态模型
```typescript
interface ValidationState {
  // 字段级验证
  fields: {
    [fieldName: string]: {
      value: any;
      errors: string[];
      touched: boolean;
      dirty: boolean;
      valid: boolean;
    }
  };
  
  // 步骤级验证
  steps: {
    [step: number]: {
      valid: boolean;
      completed: boolean;
      errors: string[];
    }
  };
  
  // 表单级验证
  form: {
    valid: boolean;
    submitted: boolean;
    submitting: boolean;
  };
}
```

## 4. 导航流程

### 4.1 前进导航（带验证）
```typescript
function handleNext(currentStep: WizardStep, formData: FormData): boolean {
  // 验证当前步骤
  const isValid = validateStep(currentStep, formData);
  
  if (!isValid) {
    // 显示验证错误
    displayValidationErrors(currentStep);
    return false;
  }
  
  // 标记步骤完成
  markStepAsCompleted(currentStep);
  
  // 导航到下一步
  if (currentStep < 3) {
    navigateToStep(currentStep + 1);
  }
  
  return true;
}
```

### 4.2 后退导航（保留数据）
```typescript
function handleBack(currentStep: WizardStep): void {
  if (currentStep > 1) {
    // 保留所有已输入数据
    preserveFormData();
    
    // 导航到上一步
    navigateToStep(currentStep - 1);
    
    // 恢复步骤状态
    restoreStepState(currentStep - 1);
  }
}
```

### 4.3 最终提交
```typescript
function handleSubmit(formData: FormData): Promise<SubmitResult> {
  // 验证所有步骤
  const allValid = [1, 2].every(step => validateStep(step, formData));
  
  if (!allValid) {
    return Promise.reject(new Error('表单验证未通过'));
  }
  
  // 准备提交数据
  const submissionData = prepareSubmission(formData);
  
  // 模拟API调用
  return mockSubmitAPI(submissionData)
    .then(result => {
      markFormAsSubmitted();
      return result;
    })
    .catch(error => {
      handleSubmissionError(error);
      throw error;
    });
}
```

## 5. 约束确认

### 约束1: TypeScript + React框架
- 使用TypeScript进行类型安全开发
- 使用React函数组件和Hooks
- 所有组件都有完整的TypeScript接口定义

### 约束2: 手动表单验证
- 实现自定义验证逻辑
- 不使用react-hook-form、formik等表单库
- 不使用zod、yup等验证库
- 所有验证规则手动实现

### 约束3: 纯CSS样式
- 使用style标签或CSS文件
- 实现响应式布局
- 不使用Tailwind CSS
- 自定义表单样式

### 约束4: 无外部npm包
- 仅使用React和TypeScript
- 所有表单功能手动实现
- 不引入任何第三方库

### 约束5: 单文件导出
- 所有代码在一个.tsx文件中
- 使用export default导出FormWizard组件
- 组件内部定义所有子组件

### 约束6: 仅输出代码
- 文档只描述设计，不包含实现代码
- 最终实现将只包含纯TypeScript/React代码
- 无解释性注释

## 6. 关键实现细节

### 6.1 表单控件设计
1. **输入组件**:
   - 受控组件模式
   - 实时验证反馈
   - 错误状态显示
   - 占位符和标签

2. **验证反馈**:
   - 即时验证（onChange）
   - 提交时验证（onSubmit）
   - 错误消息显示
   - 成功状态指示

3. **导航控件**:
   - 上一步/下一步按钮
   - 提交按钮
   - 步骤指示器
   - 进度条

### 6.2 用户体验优化
1. **数据持久化**:
   - 使用sessionStorage临时保存
   - 页面刷新时恢复数据
   - 浏览器关闭时清理

2. **键盘导航**:
   - Enter键提交表单
   - Tab键字段间导航
   - Esc键取消编辑

3. **无障碍支持**:
   - ARIA标签和描述
   - 键盘焦点管理
   - 屏幕阅读器支持

### 6.3 错误处理
1. **验证错误**:
   - 字段级错误提示
   - 步骤级错误汇总
   - 表单级错误显示

2. **提交错误**:
   - 网络错误处理
   - 服务器错误处理
   - 重试机制

3. **恢复机制**:
   - 错误后数据保留
   - 可恢复的提交
   - 错误状态清除

## 7. 组件结构

### 7.1 主组件
- **FormWizard**: 管理整体状态和导航

### 7.2 步骤组件
- **Step1PersonalInfo**: 个人信息收集
- **Step2AddressInfo**: 地址信息收集
- **Step3Confirmation**: 确认和提交

### 7.3 支持组件
- **FormInput**: 通用输入组件
- **ValidationMessage**: 验证消息显示
- **StepIndicator**: 步骤进度指示
- **NavigationButtons**: 导航按钮组

## 8. 测试策略

1. **单元测试**: 测试验证函数和状态转换
2. **集成测试**: 测试表单流程和导航
3. **端到端测试**: 测试完整表单提交流程
4. **无障碍测试**: 测试键盘导航和屏幕阅读器兼容性

---

*文档字数: 约1980字*