"""
Препроцессор ассемблера.
Поддерживает:
  - #include "file.inc"  — включение файлов
  - #define NAME value     — макросы-константы
  - #if / #else / #endif   — условная компиляция
  - Макросы MACRO / ENDM
  - Псевдокоманды с точкой: .org, .db, .dw, .ds, .equ, .end
"""
import os
import re
import warnings


class PreprocessorError(Exception):
    """Ошибка препроцессора с номером строки"""
    def __init__(self, message, line=0):
        self.line = line
        super().__init__(f"Строка {line}: {message}")


class Preprocessor:
    """Препроцессор ассемблера"""

    def __init__(self, include_dirs=None):
        self.include_dirs = include_dirs or ['.']
        self.path_dirs = []        # Дополнительные каталоги из #path / .path
        self.defines = {}          # {имя: значение}
        self.macros = {}           # {имя: (параметры, тело)}
        self.included_files = set()
        self._line_num = 0
        self.target = "bin"  # #target: rom or bin

    # =============================================
    # ГЛАВНЫЙ ВХОД
    # =============================================

    def process(self, source, filename='<input>'):
        """
        Обработать исходный текст.
        Возвращает список строк (текст, номер_строки, имя_файла).
        """
        self._line_num = 0
        self.defines = {}  # ← Сбрасываем #define
        self.macros = {}   # ← Сбрасываем макросы
        self.path_dirs = []  # ← Сбрасываем #path
        lines = source.split('\n')
        # Расширить REPT/ENDM блоки
        lines = self._expand_rept(lines, filename)
        result = []
        self._process_lines(lines, filename, result, depth=0)
        return result

    def _process_lines(self, lines, filename, result, depth):
        """Рекурсивная обработка строк"""
        if depth > 16:
            raise PreprocessorError("Слишком глубокая вложенность #include", self._line_num)
        skip_depth = 0  # Глубина #if, которые сейчас ложны
        if_stack = []   # Стек состояний #if
        elif_accepted = []  # Стек: была ли ветвь уже принята
        i = 0
        while i < len(lines):
            self._line_num += 1
            line = lines[i]
            stripped = line.strip()
            # Пропускаем пустые строки и комментарии (включая shebang #!)
            if not stripped or stripped.startswith(';') or stripped.startswith('#!'):
                if stripped.startswith('#!'):
                    line = ';' + line.lstrip()
                result.append((line, self._line_num, filename))
                i += 1
                continue
            # === Обработка #if / #else / #endif ===
            if stripped.startswith('#if'):
                condition = stripped[3:].strip()
                # Strip comment (; ...) from condition
                if ';' in condition:
                    condition = condition.split(';')[0].strip()
                if skip_depth > 0:
                    skip_depth += 1
                    if_stack.append(False)
                    elif_accepted.append(True)
                else:
                    value = self._eval_condition(condition)
                    if_stack.append(value)
                    elif_accepted.append(value)
                    if not value:
                        skip_depth = 1
                i += 1
                continue
            if stripped.startswith('#elif'):
                if not if_stack:
                    raise PreprocessorError("#elif без #if", self._line_num)
                if skip_depth == 0:
                    # Текущий блок активен — пропускаем
                    skip_depth = 1
                elif skip_depth == 1:
                    if elif_accepted and elif_accepted[-1]:
                        pass  # Ветвь уже принята
                    else:
                        condition = stripped[5:].strip()
                        if ';' in condition:
                            condition = condition.split(';')[0].strip()
                        value = self._eval_condition(condition)
                        if_stack[-1] = value
                        if value:
                            elif_accepted[-1] = True
                        skip_depth = 0 if value else 1
                elif skip_depth > 1:
                    pass
                i += 1
                continue
            if stripped.startswith('#else'):
                if not if_stack:
                    raise PreprocessorError("#else без #if", self._line_num)
                if skip_depth == 0:
                    # Текущий блок активен — пропускаем #else
                    skip_depth = 1
                elif skip_depth == 1:
                    if elif_accepted and elif_accepted[-1]:
                        pass  # Ветвь уже принята — пропускаем #else
                    else:
                        if_stack[-1] = True
                        elif_accepted[-1] = True
                        skip_depth = 0
                elif skip_depth > 1:
                    pass
                i += 1
                continue
            if stripped.startswith('#endif'):
                if not if_stack:
                    raise PreprocessorError("#endif без #if", self._line_num)
                if skip_depth > 0:
                    skip_depth -= 1
                if_stack.pop()
                if elif_accepted:
                    elif_accepted.pop()
                i += 1
                continue
            # === IF / ENDIF / ELSE без # (условная сборка) ===
            # ВАЖНО: до проверки skip_depth, чтобы вложенные IF/ENDIF работали
            if re.match(r'^IF\b', stripped, re.IGNORECASE):
                condition = stripped[2:].strip()
                if skip_depth > 0:
                    skip_depth += 1
                    if_stack.append(False)
                else:
                    value = self._eval_condition(condition)
                    if_stack.append(value)
                    if not value:
                        skip_depth = 1
                i += 1
                continue
            if re.match(r'^ENDIF\b', stripped, re.IGNORECASE):
                if not if_stack:
                    raise PreprocessorError("ENDIF без IF", self._line_num)
                if skip_depth > 0:
                    skip_depth -= 1
                if_stack.pop()
                i += 1
                continue
            if re.match(r'^ELSE\b', stripped, re.IGNORECASE):
                if not if_stack:
                    raise PreprocessorError("ELSE без IF", self._line_num)
                if skip_depth == 0:
                    skip_depth = 1
                elif skip_depth == 1:
                    if_stack[-1] = not if_stack[-1]
                    skip_depth = 0 if if_stack[-1] else 1
                elif skip_depth > 1:
                    pass
                i += 1
                continue
            # Пропускаем строки внутри ложных #if
            if skip_depth > 0:
                i += 1
                continue
            # === Пропускаем информационные директивы zasm ===
            if stripped.startswith('#target'):
                parts = stripped.split()
                if len(parts) > 1:
                    self.target = parts[1].lower()
                i += 1
                continue
            if stripped.startswith('#charset'):
                i += 1
                continue
            # === Обработка #path / .path (дополнительные каталоги поиска) ===
            m_path = re.match(r'^#?\.?path\s+["\']([^"\']+)["\']', stripped, re.IGNORECASE)
            if m_path:
                path_dir = m_path.group(1)
                # Разрешить относительный путь от каталога текущего файла
                if not os.path.isabs(path_dir) and filename != '<input>':
                    base = os.path.dirname(os.path.abspath(filename))
                    path_dir = os.path.normpath(os.path.join(base, path_dir))
                else:
                    path_dir = os.path.normpath(os.path.abspath(path_dir))
                if path_dir not in self.path_dirs:
                    self.path_dirs.append(path_dir)
                i += 1
                continue
            # .asm8080 / .8080 — указание целевого CPU (информационно)
            if re.match(r'^\.asm8080\b', stripped, re.IGNORECASE) or re.match(r'^\.8080\b', stripped, re.IGNORECASE):
                i += 1
                continue
            # === XDEF / XREF / SECTION — no-op (экспорт/импорт/секция) ===
            if re.match(r'^(XDEF|XREF|SECTION|CPU|ASEG|TITLE|\.TITLE|PUBLIC|EXTERN|MODULE)\b', stripped, re.IGNORECASE):
                i += 1
                continue
            # === Обработка M80 include (без #) ===
            m_inc = re.match(r'^include\s+["\']([^"\']+)["\']', stripped, re.IGNORECASE)
            if m_inc:
                inc_file = m_inc.group(1)
                cur_dir = os.path.dirname(os.path.abspath(filename)) if filename != '<input>' else None
                self._process_include(inc_file, result, depth, current_dir=cur_dir)
                i += 1
                continue
            # === Обработка #include ===
            if stripped.startswith('#include'):
                inc_file = self._parse_include(stripped)
                if inc_file:
                    cur_dir = os.path.dirname(os.path.abspath(filename)) if filename != '<input>' else None
                    self._process_include(inc_file, result, depth, current_dir=cur_dir)
                i += 1
                continue
            # === Обработка #define ===
            if stripped.startswith('#define'):
                self._parse_define(stripped)
                i += 1
                continue
            # === Обработка макросов MACRO / ENDM ===
            if self._is_macro_definition(stripped):
                i = self._parse_macro_definition(lines, i, filename)
                continue
            # === Подстановка #define и макросов ===
            processed = self._substitute(line)
            # zasm: если вся строка в <...>, снимаем обёртку
            stripped_proc = processed.strip()
            if stripped_proc.startswith('<') and stripped_proc.endswith('>'):
                depth = 0
                for idx, ch in enumerate(stripped_proc):
                    if ch == '<':
                        depth += 1
                    elif ch == '>':
                        depth -= 1
                        if depth == 0 and idx == len(stripped_proc) - 1:
                            indent = processed[:len(processed) - len(processed.lstrip())]
                            processed = indent + stripped_proc[1:-1]
                            break
            # === Псевдокоманды с точкой ===
            processed = self._normalize_dot_directives(processed)
            # Макрос может вернуть несколько строк — разбиваем
            proc_lines = processed.split('\n')
            for pl in proc_lines:
                result.append((pl, self._line_num, filename))
                self._line_num += 1
            i += 1
        if if_stack:
            raise PreprocessorError("Незакрытый #if", self._line_num)

    # =============================================
    # ОБРАБОТКА #include
    # =============================================

    def _parse_include(self, line):
        """Разобрать #include "file" или #include <file>"""
        m = re.match(r'#include\s+["<]([^">]+)[">]', line)
        if m:
            return m.group(1)
        # Без кавычек
        m = re.match(r'#include\s+(\S+)', line)
        if m:
            return m.group(1)
        return None

    def _process_include(self, inc_file, result, depth, current_dir=None):
        """Обработать включаемый файл.
        
        Порядок поиска:
        1. Каталог текущего файла (current_dir) — для относительных путей
        2. Каталоги из #path / .path (в порядке объявления)
        3. include_dirs (каталог главного файла, CWD)
        """
        full_path = None
        # Строим список каталогов поиска в правильном порядке
        search_dirs = []
        # 1. Каталог текущего файла — всегда первым
        if current_dir:
            search_dirs.append(current_dir)
        # 2. Каталоги из #path
        for d in self.path_dirs:
            if d not in search_dirs:
                search_dirs.append(d)
        # 3. Базовые include_dirs
        for d in self.include_dirs:
            if d not in search_dirs:
                search_dirs.append(d)
        
        for dir_path in search_dirs:
            candidate = os.path.join(dir_path, inc_file)
            if os.path.exists(candidate):
                full_path = candidate
                break

        if full_path is None:
            searched = ', '.join(search_dirs) if search_dirs else '(none)'
            raise PreprocessorError(
                f"Файл не найден: {inc_file} (искали в: {searched})", self._line_num)

        if full_path in self.included_files:
            return  # Уже включён

        self.included_files.add(full_path)

        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            lines = content.split('\n')
            saved_line = self._line_num
            self._line_num = 0
            self._process_lines(lines, inc_file, result, depth + 1)
            self._line_num = saved_line
        except OSError as e:
            raise PreprocessorError(f"Ошибка чтения {inc_file}: {e}", self._line_num)

    # =============================================
    # ОБРАБОТКА #define
    # =============================================

    def _parse_define(self, line):
        """Разобрать #define NAME value"""
        m = re.match(r'#define\s+(\w+)\s*(.*)', line)
        if m:
            name = m.group(1)
            value = m.group(2).strip()
            # Убрать комментарии // и ;
            value = re.sub(r'//.*$', '', value).strip()
            value = re.sub(r';.*$', '', value).strip()
            self.defines[name] = value

    def _substitute(self, line):
        """Подставить #define и макросы в строку. Поддерживает вложенные макросы."""
        result = line
        for _depth in range(10):  # Макс. 10 уровней вложенности
            old_result = result
            # Подстановка #define (от длинных к коротким)
            # Split by quotes to avoid substituting inside strings
            _qpat = '("[^"]*"|' + chr(39) + '[^' + chr(39) + ']*' + chr(39) + ')'
            _parts = re.split(_qpat, result)
            for _pi in range(0, len(_parts), 2):  # Even indices = unquoted
                for name in sorted(self.defines.keys(), key=len, reverse=True):
                    if name in _parts[_pi]:
                        _val = str(self.defines[name])
                        if not re.match(r'^(0[xX][0-9a-fA-F]+|\d+)$', _val):
                            if not (_val.startswith('(') and _val.endswith(')')):
                                _val = f'({_val})'
                        pattern = r'\b' + re.escape(name) + r'\b'
                        _parts[_pi] = re.sub(pattern, _val, _parts[_pi])
                result = ''.join(_parts)
            # Подстановка макросов
            expanded = False
            for name, (params, body) in self.macros.items():
                pattern = r'\b' + re.escape(name) + r'\b'
                if re.search(pattern, result, re.IGNORECASE):
                    result = self._expand_macro(result, name, params, body)
                    expanded = True
                    break  # Перезапуск цикла после расширения
            if not expanded and result == old_result:
                break
        return result

    # =============================================
    # ОБРАБОТКА МАКРОСОВ
    # =============================================

    def _is_macro_definition(self, line):
        # Format: NAME MACRO [params] / NAME: MACRO [params]
        m = re.match(r'(\w+):?\s+MACRO\b', line, re.IGNORECASE)
        if m:
            return m is not None
        # Format: NAME .macro [params] / NAME: .macro [params]
        m = re.match(r'(\w+):?\s+\.macro\b', line, re.IGNORECASE)
        if m:
            return m is not None
        # Format: .macro NAME [params] / macro NAME [params]
        m = re.match(r'\.?macro\s+(\w+)', line, re.IGNORECASE)
        if m:
            return m is not None
        return None

    def _parse_macro_definition(self, lines, start_i, filename):
        """Разобрать определение макроса, вернуть индекс следующей строки"""
        line = lines[start_i].strip()
        m = re.match(r'(\w+):?\s+MACRO\s*(.*)', line, re.IGNORECASE)
        if not m:
            m = re.match(r'(\w+):?\s+\.macro\s*(.*)', line, re.IGNORECASE)
        if not m:
            m = re.match(r'\.?macro\s+(\w+)\s*(.*)', line, re.IGNORECASE)
        if not m:
            return start_i + 1

        macro_name = m.group(1)
        params_str = m.group(2).strip()
        params = [p.strip() for p in params_str.split(',') if p.strip()]

        # Собираем тело до ENDM
        body = []
        i = start_i + 1
        while i < len(lines):
            self._line_num += 1
            body_line = lines[i]
            if body_line.strip().upper() in ('ENDM', '.ENDM'):
                i += 1
                break
            body.append(body_line)
            i += 1
        else:
            raise PreprocessorError(f"Макрос {macro_name}: нет ENDM", self._line_num)

        self.macros[macro_name] = (params, body)
        return i

    def _expand_macro(self, line, macro_name, params, body):
        r"""Развернуть макрос в строке. Поддерживает &PARAM, %PARAM, #PARAM, \PARAM (zasm)."""
        # Ищем вызов макроса с параметрами
        pattern = r'\b' + re.escape(macro_name) + r'\s*(.*)'
        m = re.search(pattern, line, re.IGNORECASE)
        if not m:
            return line

        args_str = m.group(1).strip()
        args = self._split_macro_args(args_str)

        # Плейсхолдеры для защиты значений аргументов от повторной подстановки
        placeholders = {}
        for j in range(len(args)):
            placeholders[j] = '\x00ARG{}\x00'.format(j)

        # Подставляем параметры в тело
        expanded = []
        for body_line in body:
            result = body_line
            for j, param in enumerate(params):
                if j < len(args):
                    clean = param.lstrip('&%#\\')
                    ph = placeholders[j]
                    # Заменяем все префиксные формы (case-insensitive)
                    for prefix in ('&', '%', '#', '\\'):
                        token = prefix + clean
                        result = re.sub(
                            re.escape(token) + r'(?![A-Za-z0-9_])',
                            ph, result, flags=re.IGNORECASE
                        )
                    # Простой параметр (word boundary)
                    if clean:
                        result = re.sub(
                            r'\b' + re.escape(clean) + r'\b',
                            ph, result, flags=re.IGNORECASE
                        )
            # Заменяем плейсхолдеры на реальные аргументы
            for j, ph in placeholders.items():
                result = result.replace(ph, args[j])
            expanded.append(result)

        # Заменяем вызов макроса на развёрнутое тело
        prefix = line[:m.start()]
        return prefix + '\n'.join(expanded)

    def _split_macro_args(self, args_str):
        """Разбить аргументы макроса по запятым, учитывая <...> и кавычки."""
        args = []
        current = ''
        angle_depth = 0
        in_quotes = False
        quote_char = None

        for ch in args_str:
            if angle_depth > 0:
                current += ch
                if ch == '<':
                    angle_depth += 1
                elif ch == '>':
                    angle_depth -= 1
            elif ch in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = ch
                elif ch == quote_char:
                    in_quotes = False
                current += ch
            elif ch == '<':
                angle_depth = 1
                current += ch
            elif ch == ',' and not in_quotes:
                args.append(current.strip())
                current = ''
            else:
                current += ch

        if current.strip():
            args.append(current.strip())

        return args

    # =============================================
    # НОРМАЛИЗАЦИЯ ПСЕВДОКОМАНД С ТОЧКОЙ
    # =============================================


    # =============================================
    # Обработка REPT/ENDM (повтор блока)
    # =============================================
    
    def _expand_rept(self, lines, filename):
        """Расширить блоки REPT n ... ENDM в n копий. Поддерживает .REPT."""
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            m = re.match(r'^\.?REPT\s+(\d+)', stripped, re.IGNORECASE)
            if m:
                count = int(m.group(1))
                # Найти ENDM
                body = []
                j = i + 1
                while j < len(lines):
                    if re.match(r'^\.?ENDM\b', lines[j].strip(), re.IGNORECASE):
                        break
                    body.append(lines[j])
                    j += 1
                # Расширить: count копий
                result.append(line)  # REPT строка (будет проигнорирована ассемблером)
                for rep in range(count):
                    result.extend(body)
                result.append(lines[j] if j < len(lines) else 'ENDM')  # ENDM
                i = j + 1
            else:
                result.append(line)
                i += 1
        return result

    def _normalize_dot_directives(self, line):
        """Заменить .org, .db, .dw, .ds, .equ, .end на org, db, dw, ds, equ, end.
        Нормализация применяется только вне строковых литералов (кавычек)."""
        directives = ['org', 'db', 'dw', 'ds', 'equ', 'end', 'macro', 'endm',
                      'byte', 'word', 'space', 'ascii', 'text', 'title',
                      'include', 'define', 'if', 'else', 'endif',
                      'high', 'low', 'not', 'and', 'or', 'xor', 'mod', 'shl', 'shr']

        # Разбиваем строку на части: некавычные и кавычные (строковые литералы)
        # Кавычные части не трогаем, чтобы не повреждать строки вида "a.and.b"
        _qpat = '("[^"]*"|' + chr(39) + '[^' + chr(39) + ']*' + chr(39) + ')'
        parts = re.split(_qpat, line)
        for pi in range(0, len(parts), 2):  # Чётные индексы = вне кавычек
            seg = parts[pi]
            for d in directives:
                pattern = r'\.' + d + r'\b'
                seg = re.sub(pattern, d, seg, flags=re.IGNORECASE)
            parts[pi] = seg
        return ''.join(parts)

    # =============================================
    # ВЫЧИСЛЕНИЕ УСЛОВИЙ #if
    # =============================================

    def _eval_condition(self, condition):
        """Вычислить условие #if"""
        try:
            # Подставляем #define
            for name in sorted(self.defines.keys(), key=len, reverse=True):
                _val = str(self.defines[name])
                if not re.match(r'^(0[xX][0-9a-fA-F]+|\d+)$', _val):
                    if not (_val.startswith('(') and _val.endswith(')')):
                        _val = f'({_val})'
                pattern = r'\b' + re.escape(name) + r'\b'
                condition = re.sub(pattern, _val, condition)

            # Вычисляем выражение
            return self._eval_expression(condition) != 0
        except Exception:
            return False

    def _eval_expression(self, expr):
        """Вычислить арифметическое/логическое выражение"""
        # Подстановка #define
        for name in sorted(self.defines.keys(), key=len, reverse=True):
            _val = str(self.defines[name])
            if not re.match(r'^(0[xX][0-9a-fA-F]+|\d+)$', _val):
                if not (_val.startswith('(') and _val.endswith(')')):
                    _val = f'({_val})'
            pattern = r'\b' + re.escape(name) + r'\b'
            expr = re.sub(pattern, _val, expr)

        # Замена операторов
        expr = expr.replace('&&', ' and ')
        expr = expr.replace('||', ' or ')
        expr = expr.replace('!', ' not ')
        # C-style: single '=' means equality (==), but not '==', '<=', '>=', '!='
        import re as _re
        expr = _re.sub(r'(?<![=!<>])=(?!=)', '==', expr)

        # Безопасное вычисление
        try:
            # Разрешаем цифры, буквы, $, x, операторы и скобки
            safe_expr = re.sub(r'[^0-9A-Za-z_$x+\-*/%<>()&|~=\s]', '', expr)
            # Убираем ведущие нули из десятичных чисел (00100 -> 100)
            def _strip_zeros(m):
                s = m.group(0)
                if s.lower().startswith('0x'):
                    return s  # Шестнадцатеричное — не трогаем
                stripped = s.lstrip('0')
                return stripped if stripped else '0'
            safe_expr = re.sub(r'\b\d+\b', _strip_zeros, safe_expr)
            # Заменяем $ на 0 (текущий адрес неизвестен на этапе препроцессора)
            safe_expr = safe_expr.replace('$', '0')
            # Заменяем неизвестные идентификаторы на 0
            def _replace_unknown(m):
                name = m.group(0)
                if name in ('and', 'or', 'not', 'True', 'False'):
                    return name
                return '0'
            safe_expr = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', _replace_unknown, safe_expr)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                return eval(safe_expr)
        except Exception:
            return 0

