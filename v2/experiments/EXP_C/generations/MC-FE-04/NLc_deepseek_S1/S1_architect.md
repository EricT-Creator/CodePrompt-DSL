# MC-FE-04: 3步表单向导技术方案

## 1. 步骤状态机设计

### 1.1 状态定义
```typescript
type WizardStep = 'personal' | 'address' | 'confirmation';

interface WizardState {
  currentStep: WizardStep;
  steps: {
    personal: StepState;
    address: StepState;
    confirmation: StepState;
  };
  navigation: {
    canGoNext: boolean;
    canGoBack: boolean;
    isSubmitting: boolean;
  };
}

interface StepState {
  isValid: boolean;
  isTouched: boolean;
  isCompleted: boolean;
  errors: Record<string, string>;
  values: Record<string, any>;
}
```

### 1.2 状态转换规则
- **初始状态**: `currentStep = 'personal'`
- **向前导航**: 当前步骤验证通过 → 移动到下一步
- **向后导航**: 任何步骤 → 移动到上一步（保留数据）
- **提交状态**: 确认步骤 → 提交所有数据
- **验证状态**: 字段变化 → 实时验证 → 更新步骤有效性

### 1.3 状态机实现
- **有限状态机**: 使用useReducer管理状态转换
- **状态持久化**: 使用useEffect保存到localStorage
- **状态恢复**: 组件挂载时恢复上次状态
- **状态重置**: 提交成功后重置所有状态

## 2. 每步验证规则

### 2.1 个人信息步骤（Step 1）
```typescript
const personalValidationRules = {
  name: {
    required: true,
    minLength: 2,
    maxLength: 50,
    pattern: /^[a-zA-Z\s]+$/, // 仅字母和空格
    message: '姓名必须为2-50个字母字符'
  },
  email: {
    required: true,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    message: '请输入有效的电子邮件地址'
  },
  phone: {
    required: true,
    pattern: /^\+?[\d\s\-\(\)]{10,}$/,
    message: '请输入有效的电话号码'
  }
};
```

### 2.2 地址信息步骤（Step 2）
```typescript
const addressValidationRules = {
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
    message: '城市名称必须为2-50个字符'
  },
  state: {
    required: true,
    pattern: /^[A-Z]{2}$/, // 两个大写字母
    message: '州代码必须是两个大写字母'
  },
  zip: {
    required: true,
    pattern: /^\d{5}(-\d{4})?$/,
    message: '邮政编码必须是5位或9位格式'
  }
};
```

### 2.3 验证实现方法
- **实时验证**: 字段变化时立即验证
- **延迟验证**: blur事件触发完整验证
- **批量验证**: 导航时验证所有字段
- **错误显示**: 内联错误消息和字段高亮

## 3. 数据模型

### 3.1 TypeScript接口定义
```typescript
interface PersonalInfo {
  name: string;
  email: string;
  phone: string;
}

interface AddressInfo {
  street: string;
  city: string;
  state: string;
  zip: string;
}

interface FormData {
  personal: PersonalInfo;
  address: AddressInfo;
  submittedAt?: string;
}

interface ValidationError {
  field: string;
  message: string;
  type: 'required' | 'pattern' | 'length' | 'custom';
}

interface StepConfig {
  id: WizardStep;
  title: string;
  fields: FieldConfig[];
  validationRules: Record<string, ValidationRule>;
}

interface FieldConfig {
  name: string;
  label: string;
  type: 'text' | 'email' | 'tel';
  placeholder?: string;
  required: boolean;
}
```

### 3.2 数据流设计
- **单向数据流**: 用户输入 → 状态更新 → UI渲染
- **数据持久化**: 步骤间数据自动保存
- **数据隔离**: 每步数据独立存储和管理
- **数据合并**: 提交时合并所有步骤数据

## 4. 导航流程

### 4.1 向前导航（带验证）
```
用户点击"下一步" → 
触发当前步骤验证 → 
如果验证通过 → 
保存当前步骤数据 → 
更新currentStep到下一步 → 
重置下一步的验证状态 → 
更新导航按钮状态
```

### 4.2 向后导航（保留数据）
```
用户点击"上一步" → 
保存当前步骤数据 → 
更新currentStep到上一步 → 
恢复上一步的数据和验证状态 → 
更新导航按钮状态
```

### 4.3 提交流程
```
用户点击"提交" → 
验证所有步骤数据 → 
如果全部有效 → 
设置isSubmitting状态 → 
合并所有步骤数据 → 
发送提交请求 → 
处理响应 → 
重置表单状态或显示成功消息
```

### 4.4 导航状态管理
- **按钮状态**: 基于步骤验证和位置决定按钮可用性
- **进度指示**: 显示当前步骤和总步骤数
- **步骤跳转**: 支持直接跳转到已完成的步骤
- **导航保护**: 防止跳过未完成的步骤

## 5. 约束确认

### 5.1 TS + React
- TypeScript定义所有表单数据类型
- React函数组件配合useReducer
- 类型安全的验证规则和状态管理

### 5.2 Hand-written validation, no formik/zod
- 手动实现所有验证逻辑
- 自定义验证规则和错误消息
- 不使用任何表单验证库

### 5.3 Plain CSS, no Tailwind
- 使用纯CSS编写样式
- CSS Modules实现样式隔离
- 不使用Tailwind或任何CSS框架

### 5.4 No external deps
- 不使用任何第三方库
- 原生实现表单验证、状态管理和UI组件
- 仅依赖React和TypeScript

### 5.5 Single file, export default
- 所有代码在单个.tsx文件中
- 使用export default FormWizard
- 内部模块化组织表单步骤和验证逻辑

### 5.6 Code only
- 不包含任何外部资源
- 所有验证逻辑用代码实现
- 表单布局和样式用CSS实现