"""
Тестовый MCP Client для проверки i8080 MCP Server
Запуск: python test_mcp_client.py
"""

import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    server_url = "http://127.0.0.1:8000/sse"
    
    print(f"🔌 Подключение к MCP Server: {server_url}")
    
    try:
        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Инициализация
                await session.initialize()
                print("✅ Соединение установлено!")
                
                # === Тест 1: Список tools ===
                print("\n📋 Список инструментов (tools):")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f"  • {tool.name}: {tool.description[:60]}...")
                print(f"  Всего: {len(tools.tools)} инструментов")
                
                # === Тест 2: Список resources ===
                print("\n📚 Список ресурсов (resources):")
                resources = await session.list_resources()
                for res in resources.resources:
                    print(f"  • {res.uri}: {res.name}")
                print(f"  Всего: {len(resources.resources)} ресурсов")
                
                # === Тест 3: Список prompts ===
                print("\n💬 Список промптов (prompts):")
                prompts = await session.list_prompts()
                for prompt in prompts.prompts:
                    print(f"  • {prompt.name}: {prompt.description}")
                print(f"  Всего: {len(prompts.prompts)} промптов")
                
                # === Тест 4: Вызов get_status ===
                print("\n🔧 Вызов инструмента get_status:")
                result = await session.call_tool("get_status", {})
                for content in result.content:
                    print(f"  Результат: {content.text}")
                
                # === Тест 5: Чтение ресурса status://info ===
                print("\n📖 Чтение ресурса status://info:")
                resource = await session.read_resource("status://info")
                for content in resource.contents:
                    print(f"  {content.text}")
                
                # === Тест 6: Запись и чтение памяти ===
                print("\n🔧 Тест записи/чтения памяти:")
                
                # Записываем байт
                result = await session.call_tool("write_mem", {"addr": 0, "val": 0x3E})
                for content in result.content:
                    print(f"  Запись: {content.text}")
                
                # Читаем байт
                result = await session.call_tool("read_mem", {"addr": 0})
                for content in result.content:
                    print(f"  Чтение: {content.text}")
                
                # === Тест 7: Дизассемблирование ===
                print("\n🔧 Тест дизассемблирования:")
                
                # Записываем простую программу
                program = [0x3E, 0x55, 0xD3, 0x01, 0xC3, 0x00, 0x00]
                result = await session.call_tool("write_block", {"addr": 0, "data": program})
                for content in result.content:
                    print(f"  Запись блока: {content.text}")
                
                # Дизассемблируем
                result = await session.call_tool("disassemble", {"addr": 0, "length": 7})
                for content in result.content:
                    print(f"  Дизассемблирование:\n{content.text}")
					
			    # === Тест: Tools эмулятора ===
                print("\n🔧 Тест инструментов эмулятора:")
                
                # Сброс
                result = await session.call_tool("emu_reset", {})
                for content in result.content:
                    print(f"  Reset: {content.text}")
                
                # Состояние
                result = await session.call_tool("emu_get_state", {})
                for content in result.content:
                    print(f"  State: {content.text[:100]}...")
                
                # Установка регистра
                result = await session.call_tool("emu_set_reg", {"reg": "A", "val": 0x55})
                for content in result.content:
                    print(f"  Set A: {content.text}")
                
                # Чтение регистра
                result = await session.call_tool("emu_get_reg", {"reg": "A"})
                for content in result.content:
                    print(f"  Get A: {content.text}")
                
                # Точки останова
                result = await session.call_tool("emu_add_breakpoint", {"addr": 0x0005})
                for content in result.content:
                    print(f"  Add BP: {content.text}")
                
                result = await session.call_tool("emu_list_breakpoints", {})
                for content in result.content:
                    print(f"  List BPs: {content.text}")
                
                # Трассировка
                result = await session.call_tool("emu_trace", {"n": 5})
                for content in result.content:
                    print(f"  Trace:\n{content.text}")
                
                # Очистка
                result = await session.call_tool("emu_clear_breakpoints", {})
                for content in result.content:
                    print(f"  Clear BPs: {content.text}")
                
                print("\n✅ Все тесты завершены успешно!")
                
    except ConnectionRefusedError:
        print("❌ Ошибка: MCP Server не запущен!")
        print("   Запустите i8080 Master Controller и включите MCP Server.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())