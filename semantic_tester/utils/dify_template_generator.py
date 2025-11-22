"""
Dify Chat Tester 输入模板生成器

用于生成标准的Dify Chat Tester输出格式模板，
方便用户创建符合Semantic Tester要求的测试数据。
"""

import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from colorama import Fore, Style


class DifyTemplateGenerator:
    """Dify Chat Tester 模板生成器"""

    # 标准的Dify Chat Tester输出列结构
    STANDARD_COLUMNS = [
        "时间戳",
        "角色", 
        "原始问题",
        "Dify响应",
        "是否成功",
        "错误信息",
        "对话ID"
    ]

    # 支持的供应商响应列名
    SUPPLIER_RESPONSE_COLUMNS = {
        "dify": "Dify响应",
        "openai": "OpenAI兼容接口响应", 
        "anthropic": "Anthropic兼容接口响应",
        "iflow": "iFlow响应",
        "gemini": "Gemini响应"
    }

    def __init__(self):
        """初始化模板生成器"""
        self.templates_dir = "templates"
        self._ensure_templates_dir()

    def _ensure_templates_dir(self):
        """确保模板目录存在"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)

    def generate_basic_template(self, supplier: str = "dify") -> str:
        """
        生成基础的Dify Chat Tester模板

        Args:
            supplier: 供应商名称 (dify, openai, anthropic, iflow, gemini)

        Returns:
            str: 生成的模板文件路径
        """
        # 根据供应商确定响应列名
        response_col = self.SUPPLIER_RESPONSE_COLUMNS.get(supplier.lower(), f"{supplier}响应")
        
        # 构建列结构
        columns = self.STANDARD_COLUMNS.copy()
        # 替换响应列
        columns[3] = response_col
        
        # 创建示例数据
        sample_data = self._create_sample_data(columns, supplier)
        
        # 确保数据格式正确
        if not isinstance(sample_data, dict):
            sample_data = dict(sample_data)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dify_chat_tester_{supplier}_template_{timestamp}.xlsx"
        filepath = os.path.join(self.templates_dir, filename)
        
        # 保存Excel文件 - 创建空模板
        try:
            # 创建简单的空模板，用户可以自行填写
            empty_data = {col: "" for col in columns}
            df = pd.DataFrame([empty_data], columns=columns)
            df.to_excel(filepath, index=False, engine='openpyxl')
        except Exception as e:
            print(f"❌ 模板生成失败: {e}")
            return None
        
        print(f"{Fore.GREEN}✅ 已生成 {supplier} 模板: {filepath}{Style.RESET_ALL}")
        return filepath

    def generate_multi_supplier_template(self, suppliers: List[str]) -> str:
        """
        生成多供应商模板

        Args:
            suppliers: 供应商列表

        Returns:
            str: 生成的模板文件路径
        """
        # 构建多供应商列结构
        columns = ["时间戳", "角色", "原始问题"]
        
        # 添加各供应商响应列
        for supplier in suppliers:
            response_col = self.SUPPLIER_RESPONSE_COLUMNS.get(supplier.lower(), f"{supplier}响应")
            columns.append(response_col)
        
        # 添加标准列
        columns.extend(["是否成功", "错误信息", "对话ID"])
        
        # 创建示例数据
        sample_data = self._create_multi_supplier_sample_data(columns, suppliers)
        
        # 确保数据格式正确
        if not isinstance(sample_data, dict):
            sample_data = dict(sample_data)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        supplier_names = "_".join(suppliers)
        filename = f"dify_chat_tester_multi_{supplier_names}_template_{timestamp}.xlsx"
        filepath = os.path.join(self.templates_dir, filename)
        
        # 保存Excel文件 - 创建空模板
        try:
            # 创建简单的空模板，用户可以自行填写
            empty_data = {col: "" for col in columns}
            df = pd.DataFrame([empty_data], columns=columns)
            df.to_excel(filepath, index=False, engine='openpyxl')
        except Exception as e:
            print(f"❌ 模板生成失败: {e}")
            return None
        
        print(f"{Fore.GREEN}✅ 已生成多供应商模板: {filepath}{Style.RESET_ALL}")
        return filepath

    def _create_sample_data(self, columns: List[str], supplier: str) -> Dict[str, Any]:
        """创建单供应商示例数据"""
        sample_data = {
            "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "角色": "员工",
            "原始问题": "什么是人工智能？请简单介绍一下。",
            "是否成功": True,
            "错误信息": "",
            "对话ID": f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        # 添加供应商特定的响应
        response_col = self.SUPPLIER_RESPONSE_COLUMNS.get(supplier.lower(), f"{supplier}响应")
        sample_data[response_col] = self._get_sample_response(supplier)
        
        # 确保所有列都有值
        for col in columns:
            if col not in sample_data:
                sample_data[col] = ""
        
        return sample_data

    def _create_multi_supplier_sample_data(self, columns: List[str], suppliers: List[str]) -> Dict[str, Any]:
        """创建多供应商示例数据"""
        sample_data = {
            "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "角色": "员工", 
            "原始问题": "什么是人工智能？请简单介绍一下。",
            "是否成功": True,
            "错误信息": "",
            "对话ID": f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        # 添加各供应商响应
        for supplier in suppliers:
            response_col = self.SUPPLIER_RESPONSE_COLUMNS.get(supplier.lower(), f"{supplier}响应")
            sample_data[response_col] = self._get_sample_response(supplier)
        
        # 确保所有列都有值
        for col in columns:
            if col not in sample_data:
                sample_data[col] = ""
        
        return sample_data

    def _get_sample_response(self, supplier: str) -> str:
        """获取供应商示例回答"""
        responses = {
            "dify": "您好！人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。这包括学习、推理、问题解决、感知和语言理解等能力。",
            "openai": "人工智能是一种模拟人类智能的技术，通过算法和大数据让机器能够学习、推理和决策。它在图像识别、自然语言处理、自动驾驶等领域有广泛应用。",
            "anthropic": "人工智能是指由机器展现的智能，特别是计算机系统模拟人类智能过程的能力。包括学习（获取信息和规则）、使用规则进行推理或结论，以及自我修正等。",
            "iflow": "人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的技术科学。它试图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。",
            "gemini": "人工智能是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。这些系统可以通过学习大量数据来识别模式、做出决策和解决问题。"
        }
        
        return responses.get(supplier.lower(), "这是一个AI回答示例。请根据您的具体需求修改此内容。")

    def list_available_templates(self) -> List[str]:
        """列出可用的模板文件"""
        if not os.path.exists(self.templates_dir):
            return []
        
        templates = []
        for file in os.listdir(self.templates_dir):
            if file.endswith('.xlsx'):
                templates.append(os.path.join(self.templates_dir, file))
        
        return sorted(templates)

    def show_template_info(self):
        """显示模板生成信息"""
        print(f"\n{Fore.CYAN}=== Dify Chat Tester 模板生成器 ==={Style.RESET_ALL}")
        print(f"模板保存目录: {self.templates_dir}")
        print()
        print("支持的供应商:")
        for key, value in self.SUPPLIER_RESPONSE_COLUMNS.items():
            print(f"  • {key}: {value}")
        print()
        print("使用说明:")
        print("1. 生成模板后，在Excel中填写实际的测试问题")
        print("2. 使用Dify Chat Tester或其他工具生成AI回答")
        print("3. 保存后可直接用于Semantic Tester进行语义评估")
        print()
        print("标准列结构:")
        for i, col in enumerate(self.STANDARD_COLUMNS, 1):
            print(f"  {i}. {col}")


def create_dify_template_interactive():
    """交互式创建Dify模板"""
    generator = DifyTemplateGenerator()
    generator.show_template_info()
    
    print(f"\n{Fore.YELLOW}请选择模板类型:{Style.RESET_ALL}")
    print("1. 单供应商模板")
    print("2. 多供应商模板")
    print("3. 查看现有模板")
    print("4. 返回")
    
    choice = input(f"\n{Fore.YELLOW}请选择 (1-4): {Style.RESET_ALL}").strip()
    
    if choice == "1":
        print(f"\n{Fore.YELLOW}请选择供应商:{Style.RESET_ALL}")
        for i, key in enumerate(generator.SUPPLIER_RESPONSE_COLUMNS.keys(), 1):
            print(f"{i}. {key}")
        
        try:
            supplier_choice = int(input(f"{Fore.YELLOW}请选择 (1-{len(generator.SUPPLIER_RESPONSE_COLUMNS)}): {Style.RESET_ALL}"))
            suppliers = list(generator.SUPPLIER_RESPONSE_COLUMNS.keys())
            if 1 <= supplier_choice <= len(suppliers):
                supplier = suppliers[supplier_choice - 1]
                generator.generate_basic_template(supplier)
            else:
                print(f"{Fore.RED}❌ 无效选择{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}❌ 请输入有效数字{Style.RESET_ALL}")
    
    elif choice == "2":
        print(f"\n{Fore.YELLOW}请选择供应商 (可多选，用逗号分隔):{Style.RESET_ALL}")
        for i, key in enumerate(generator.SUPPLIER_RESPONSE_COLUMNS.keys(), 1):
            print(f"{i}. {key}")
        
        supplier_input = input(f"{Fore.YELLOW}请输入序号 (例如: 1,3,5): {Style.RESET_ALL}").strip()
        try:
            indices = [int(x.strip()) - 1 for x in supplier_input.split(',')]
            suppliers = list(generator.SUPPLIER_RESPONSE_COLUMNS.keys())
            selected_suppliers = [suppliers[i] for i in indices if 0 <= i < len(suppliers)]
            
            if selected_suppliers:
                generator.generate_multi_supplier_template(selected_suppliers)
            else:
                print(f"{Fore.RED}❌ 无效选择{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}❌ 请输入有效的序号{Style.RESET_ALL}")
    
    elif choice == "3":
        templates = generator.list_available_templates()
        if templates:
            print(f"\n{Fore.GREEN}现有模板:{Style.RESET_ALL}")
            for i, template in enumerate(templates, 1):
                print(f"{i}. {os.path.basename(template)}")
        else:
            print(f"\n{Fore.YELLOW}暂无模板文件{Style.RESET_ALL}")
    
    elif choice == "4":
        return
    
    else:
        print(f"{Fore.RED}❌ 无效选择{Style.RESET_ALL}")


if __name__ == "__main__":
    create_dify_template_interactive()
