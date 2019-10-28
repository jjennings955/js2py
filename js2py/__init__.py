import astor
import pprint
import glob
import distutils.dir_util
import os
import pprint
import esprima
from pampy import match, _
import ast
from ast import *

from esprima.visitor import ToDictVisitor


def unroll_body(b):
    out = []
    for el in b:
        if isinstance(el, list):
            out.extend(el)
        else:
            if el:
                out.append(el)
    return out

def exists(node, query, alternate=None):
    last_node = None
    try:
        def _exists(node, query):
            nonlocal last_node
            if not node:
                return alternate
            last_node = node
            if len(query) >= 1:
                return hasattr(node, query[0]) and _exists(getattr(node, query[0]), query[1:])
            else:
                if hasattr(node, query[0]) and hasattr(getattr(node, query[0]), query[1]):
                    last_node = getattr(getattr(node, query[0]), query[1])
                    return True
                else:
                    return False

        if _exists(node, query.split('.')[1:]):
            return last_node
        else:
            return alternate
    except Exception as e:
        return alternate

class MyVisitor(ToDictVisitor):
    def __init__(self):
        ToDictVisitor.__init__(self)
        self._funcs = {}
        self._classes = {}

    level = 0
    anon_cnt = 0

    def transform_StaticMemberExpression(self, node, metadata):
        l = node.object.python_ast
        r = node.property.python_ast
        if exists(node, '.expression.callee'):
            out = []
            for arg in node.expression.arguments[1:]:
                out.append(arg.python_string)
            node.python_string = '\n'.join(out)

        if node.computed:
            node.python_string = ("{a}[{b}]".format(a=l, b=r))
            node.python_ast = Subscript(value=l, slice=Index(value=r, ctx=Load()))
        else:
            node.python_string = ("{a}.{b}".format(a=l, b=r))

            node.python_ast = Attribute(value=l.value if isinstance(l, Expr) else l, attr=r.id, ctx=Load())
        return node

    def transform_MemberExpression(self, node, metadata):
        l = node.object.python_ast
        r = node.property.python_ast
        if exists(node, '.expression.callee'):
            out = []
            for arg in node.expression.arguments[1:]:
                out.append(arg.python_string)
            node.python_string = '\n'.join(out)

        if node.computed:
            node.python_string = ("{a}[{b}]".format(a=l, b=r))
            node.python_ast = Subscript(value=l, slice=Index(value=r, ctx=Load()))
        else:
            node.python_string = ("{a}.{b}".format(a=l, b=r))
            node.python_ast = Attribute(value=l, attr=r, ctx=Load())
        return node

    def transform_Object(self, obj, metadata):
        """Called if no explicit transform function exists for an Object."""
        if obj.type.endswith('MemberExpression'):
            return self.transform_MemberExpression(obj, metadata)
        if obj.type == 'Program':
            return self.transform_Program(obj, metadata)
        if obj.type == "ExpressionStatement":
            return self.transform_ExpressionStatement(obj, metadata)
        if obj.type == "transform_ObjectExpression":
            return self.transform_ObjectExpression(obj, metadata)
        if obj.type == "Function_Expression":
            return self.transform_FunctionExpression(obj, metadata)

    def transform_ExportDefaultDeclaration(self, node, params):
        node.python_ast = node.declaration.python_ast
        return node

    def transform_FunctionExpression(self, node, params):
        return self.transform_FunctionDeclaration(node, params)

    def transform_ImportDeclaration(self, node, params):
        node.python_ast = ImportFrom(module=node.source.python_ast.s,
                                     names=[alias(name=imp.imported.name, asname=None) if
                                            imp.type == 'ImportSpecifier' else alias(name='*', asname=None) for imp in node.specifiers ], level=0)

        return node

    def transform_MetaProperty(self, node, params):
        node.python_ast = Pass()
        return node

    def transform_ThisExpression(self, node, params):
        node.python_ast = Name(id='self', ctx=Load())
        return node

    def transform_ReturnStatement(self, node, params):
        if node.argument and node.argument.python_ast:
            node.python_ast = Return(value=node.argument.python_ast)
        else:
            node.python_ast = Return(value=NameConstant(value=None))
        return node

    def transform_BlockStatement(self, node, params):
        if not len(node.body):
            node.python_ast = [Pass()]
        else:
            node.python_ast = unroll_body([child.python_ast for child in node.body])
        return node

    def transform_ThrowStatement(self, node, params):
        if node.argument.python_string == 'Error':
            node.argument.python_string = 'Exception'
        node.python_ast = Raise(exc=Call(func=Name(id='Exception', ctx=Load()), args=[n.python_ast for n in node.argument.arguments], keywords=[]), cause=None)
        return node

    def transform_AnonymousFunction(self, node, params):
        node.python_ast = Name(id="Anonymous" + "_" + str(self.anon_cnt), ctx=Load())
        if not isinstance(node.body.python_ast, list):
            node.body.python_ast = [node.body.python_ast]
        num = len(node.body.python_ast)
        node.body.python_ast[num - 1] = Return(value=node.body.python_ast[num - 1])
        self._funcs["Anonymous" + "_" + str(self.anon_cnt)] = FunctionDef(
            name="Anonymous" + "_" + str(self.anon_cnt),
            args=arguments(args=[arg(arg=argument.name, annotation=None) for argument in
                                 node.params], vararg=None, kwonlyargs=[], kw_defaults=[],
                           kwarg=None, defaults=[]),
            body=unroll_body(node.body.python_ast),
            decorator_list=[], returns=None)
        self.node = None
        self.anon_cnt += 1
        return node

    def transform_FunctionDeclaration(self, node, params):
        if node.id:
            func_name = node.id.name
            node.python_ast = None
            node.func_name = func_name
            func_body = []
            self._funcs[func_name] = FunctionDef(name=func_name,
                                                 args=arguments(
                                                     args=[arg(arg=argument.name, annotation=None) for argument in
                                                           node.params], vararg=None, kwonlyargs=[], kw_defaults=[],
                                                     kwarg=None, defaults=[]),
                                                 body=unroll_body(node.body.python_ast),
                                                 decorator_list=[], returns=None)
        else:
            return self.transform_AnonymousFunction(node, params)

        return node

    def transform_AssignmentExpression(self, node, metadata):
        node.left.python_ast.ctx = Store()
        if node.operator in ['+=', '++', '-=', '--']:
            return self.transform_UpdateExpression(node, metadata)
        try:
            source_left = astor.to_source(node.left.python_ast).strip()
            source_right = astor.to_source(node.right.python_ast).strip()

            if source_left.endswith('.prototype'):
                class_name = node.left.python_ast.value.id
                if class_name not in self._classes:
                    class_obj = ClassDef(name=class_name, bases=[], decorator_list=[])
                    class_obj.body = []
                if source_right.startswith('Object.assign(Object.create('):
                    for i, key in enumerate(node.right.python_ast.args[1].keys):
                        real_name = key.id
                        rhs = node.right.python_ast.args[1].values[i]
                        if isinstance(rhs, Name):
                            placeholder_name = rhs.id
                            anon = self._funcs[placeholder_name]
                            if real_name == 'constructor':
                                real_name = '__init__'
                            self._funcs[placeholder_name].python_ast = None

                            anon.name = real_name
                            anon.args.args.insert(0, arg(arg='self', annotation=None))
                            class_obj.body.append(anon)
                            class_obj.body = unroll_body(class_obj.body)
                else:
                    pass

                self._classes[class_name] = class_obj
                node.python_ast = []
                return node
            elif '.prototype.' in source_left and isinstance(node.right.python_ast, Name):
                tokens = source_left.split('.')
                class_name = tokens[0]
                if class_name in self._classes:
                    func_name = source_right
                    fun = self._funcs.get(func_name, node.right.python_ast.id)
                    if fun.name == class_name:
                        fun.name = "__init__"
                    else:
                        fun.name = tokens[-1]

                    fun.args.args.insert(0, arg(arg='self', annotation=None))
                    self._classes[class_name].body.append(fun)

                    self._classes[class_name].body = unroll_body(self._classes[class_name].body)
                    node.python_ast = []
                    return node


        except (AttributeError, IndexError) as e:
            pass
        node.python_ast = Assign(targets=[node.left.python_ast], value=node.right.python_ast, ctx=Load())

        return node

    def transform_Literal(self, node, metadata):
        node.python_string = repr(node.value)
        if node.raw == 'null':
            node.python_ast = NameConstant(value=None)
        if isinstance(node.value, int) or isinstance(node.value, float):
            node.python_ast = Num(n=node.value)
        if isinstance(node.value, str):
            node.python_ast = Str(s=node.value)

        return node

    def transform_RegexLiteral(self, node, metadata):
        node.python_ast = ast.parse(str(node.value)).body[0].value
        return node

    def transform_NewExpression(self, node, metadata):
        return self.transform_CallExpression(node, metadata)

    def transform_CallExpression(self, node, metadata):
        if node.callee.type == "Super":
            node.callee.python_ast = Call(func=Name(id='super', ctx=Load()),
                                          args=[Name(id='self', ctx=Load()),
                                                NameConstant(value=None)], keywords=[])
            node.python_ast = Call(func=Attribute(value=node.callee.python_ast, attr='__init__', ctx=Load()),
                                   args=[_arg.python_ast for _arg in node.arguments], keywords=[])
        else:
            node.python_ast = Call(func=node.callee.python_ast, args=[_arg.python_ast for _arg in node.arguments],
                                   keywords=[])
        src = astor.to_source(node.callee.python_ast)
        if src.startswith("QUnit."):
            test_name = node.python_ast.args[0].s
            test_func = node.python_ast.args[1].id
            func = self._funcs.pop(test_func)
            func.name = "test_" + test_name
            node.python_ast = func

        if src.startswith("Object.assign"):
            if isinstance(node.python_ast.args[0], Attribute):
                class_name = node.python_ast.args[0].value.id
            elif isinstance(node.python_ast.args[0], Name):
                class_name = node.python_ast.args[0].id
            else:
                print(ast.dump(node.python_ast.args))

            print(class_name)
            class_obj = self._classes.get(class_name, ClassDef(name=class_name, bases=[], decorator_list=[], body=[]))
            self._classes[class_name] = class_obj

            for i, key in enumerate(node.python_ast.args[1].keys):
                real_name = key.id
                rhs = node.python_ast.args[1].values[i]
                if isinstance(rhs, Name):
                    placeholder_name = rhs.id
                    anon = self._funcs[placeholder_name]
                    if real_name == 'constructor':
                        real_name = '__init__'
                    self._funcs[placeholder_name].python_ast = None

                    anon.name = real_name

                    anon.args.args.insert(0, arg(arg='self', annotation=None))
                    class_obj.body.append(anon)
                    class_obj.body = unroll_body(class_obj.body)
            node.python_ast = Pass()

        return node

    def transform_Identifier(self, node, metadata):
        if node.name == 'undefined':
            node.python_string = 'None'
            node.python_ast = NameConstant(value=None)
        else:
            node.python_ast = Name(id=node.name, ctx=Load())
        return node

    def transform_ArrayExpression(self, node, metadata):
        elements = []
        for child in node.elements:
            elements.append(child.python_ast)
        node.python_ast = List(elts=elements, ctx=Load())
        return node

    def transform_Property(self, node, metadata):
        node.python_ast = Attribute(value=node.key.python_ast, attr=node.value, ctx=Load())
        return node

    def transform_ObjectExpression(self, node, metadata):
        keys = []
        vals = []
        for prop in node.properties:
            keys.append(prop.key.python_ast)
            vals.append(prop.value.python_ast)
        node.python_ast = Dict(keys=keys, values=vals)
        return node

    def transform_Program(self, node, metadata):
        body = list(self._classes.values())
        body = list(self._funcs.values())
        body.extend(unroll_body(n.python_ast for n in node.body if n != None))

        node.python_ast = Module(body=body)
        return node

    def transform_ExpressionStatement(self, node, metadata):
        if isinstance(node.expression.python_ast, Assign):
            node.python_ast = node.expression.python_ast
        else:
            node.python_ast = Expr(value=node.expression.python_ast)

        return node

    def transform_VariableDeclarator(self, node, metadata):
        if node.init:
            node.python_ast = Assign(targets=[Name(id=node.id.name, ctx=Store())], value=node.init.python_ast)
        else:
            node.python_ast = Assign(targets=[Name(id=node.id.name, ctx=Store())], value=NameConstant(value=None))
        return node

    def transform_VariableDeclaration(self, node, metadata):
        node.python_ast = [n.python_ast for n in node.declarations]
        return node

    def transform_IfStatement(self, node, metadata):
        if not isinstance(node.consequent.python_ast, list):
            body = [node.consequent.python_ast]
        else:
            body = node.consequent.python_ast
        node.python_ast = If(test=node.test.python_ast, body=unroll_body(body), orelse=[])

        return node

    def transform_ForInStatement(self, node, metadata):
        node.python_ast = For(target=Name(id=node.left.name, ctx=Store()),
                              iter=node.right.python_ast,
                              body=unroll_body(node.body.python_ast),
                              orelse=[])

        return node

    def transform_ForOfStatement(self, node, metadata):
        return self.transform_ForInStatement(node, metadata)

    def transform_ForStatement(self, node, metadata):
        init_ast = node.init.python_ast if node.init and node.init.python_ast else None
        test_ast = node.test.python_ast if node.test else []
        update = node.update.python_ast if node.update and node.update.python_ast else None
        body_ast = node.body.python_ast if node.body and node.body.python_ast else Pass()
        right_ast = node.right.python_ast if node.right and node.right.python_ast else None
        if node.init and node.init.type == 'SequenceExpression':
            node.python_ast = init_ast
        elif isinstance(init_ast, Assign):
            node.python_ast = [init_ast]
        else:
            node.python_ast = []
        if isinstance(init_ast, type(None)):
            pass

        if hasattr(node.init, 'python_ast'):
            if isinstance(node.init.python_ast, list):
                first_target = node.init.python_ast[0].targets[0].id
            else:
                first_target = node.init.python_ast.targets[0].id

        node.python_ast.append(While(test=test_ast, body=unroll_body([body_ast] + ([node.update.python_ast] if node.update else [])), orelse=[]))
        if len(node.python_ast) == 1:
            node.python_ast = node.python_ast[0]
        else:
            node.python_ast = unroll_body(node.python_ast)
        return node

    def transform_WhileStatement(self, node, metadata):
        test_str = node.test.python_string

        body_str = node.body.python_string
        node.python_ast = While(
            test=node.test.python_ast,
            body=unroll_body(node.body.python_ast), orelse=[])

        return node

    def transform_EmptyStatement(self, obj, metadata):
        obj.python_ast = None
        return obj

    def transform_UpdateExpression(self, node, metadata):
        op = {
            '+' : Add,
            '-' : Sub,
        }[node.operator[0]]
        if node.type == 'UpdateExpression':
            node.python_ast = AugAssign(target=node.argument.python_ast, op=op(), value=Num(n=1))
        else:
            node.python_ast = AugAssign(target=node.left.python_ast, op=op(), value=node.right.python_ast)
        return node

    def transform_UnaryExpression(self, node, metadata):
        new_op = {
            '+': UAdd,
            '-': USub,
            '~': Invert,
            '!': Not,
            'delete': Delete,
            'typeof': 'Type',
            'void': UAdd
        }[node.operator]
        unary = [UAdd, USub, Invert, Not]

        if new_op in unary:
            node.python_ast = UnaryOp(op=new_op, operand=node.argument.python_ast)
        if new_op == Delete:
            node.python_ast = Delete(targets=[node.argument.python_ast])
        else:
            node.python_ast = node.argument.python_ast

        return node

    def transform_LogicalExpression(self, obj, metadata):
        if obj.operator == '||':
            obj.python_ast = BinOp(left=obj.left.python_ast, op=Or(), right=obj.right.python_ast)
        if obj.operator == '&&':
            obj.python_ast = BinOp(left=obj.left.python_ast, op=And(), right=obj.right.python_ast)

        return obj

    def transform_ConditionalExpression(self, node, metadata):
        node.python_ast = IfExp(test=node.test.python_ast, body=node.consequent.python_ast,
                                orelse=node.alternate.python_ast)
        return node

    def transform_YieldExpression(self, node, metadata):

        node.python_ast = Yield(value=node.argument.python_ast, ctx=Load())
        return node

    def transform_SequenceExpression(self, node, metadata):

        node.python_ast = [child.python_ast for child in node.expressions]
        return node

    def transform_BreakStatement(self, node, metadata):

        node.python_ast = Break()
        return node

    def transform_SwitchStatement(self, node, metadata):
        node.python_ast = [c.python_ast for c in node.cases]

        def merge(n, rest):
            j = 0
            if not n.body:
                n.test = BoolOp(op=Or(), values=[n.test, rest[j].test])
                n.body = rest[j].body
                j += 1

            if len(rest) > j + 1:
                n.orelse = [merge(rest[j], rest[j + 1:])]
                return n
            if len(rest) == j + 1:
                n.orelse = [rest[j]]
                return n
            else:
                n.orelse = []
                return n

        node.python_ast = merge(node.python_ast[0], node.python_ast[1:])
        return node

    def transform_ArrowFunctionExpression(self, node, metadata):
        return self.transform_FunctionDeclaration(node, metadata)

    def transform_ClassDeclaration(self, node, metadata):
        class_obj = ClassDef(name=node.id.name, bases=[], decorator_list=[])
        class_obj.body = []
        for meth in node.body:
            class_obj.body.append(meth)
        node.python_ast = Pass()
        return node

    def transform_ClassBody(self, node, metadata):
        return [n.python_ast for n in node.body]

    def transform_MethodDefinition(self, node, metadata):
        func_name = node.value.python_ast.id
        func = self._funcs.pop(func_name)
        if func_name == "constructor" or node.key.name == "constructor":
            func_name = "__init__"
        else:
            func_name = node.key.name
        #
        func.name = func_name

        func.args.args.insert(0, arg(arg="self", annotation=None))
        node.python_ast = func
        return node

    def transform_SwitchCase(self, node, metadata):
        test = node.test.python_ast if hasattr(node.test, 'python_ast') else []
        node.python_ast = If(test=test, body=[c.python_ast for c in node.consequent], orelse=[])
        return node

    def transform_ContinueStatement(self, node, metadata):
        node.python_ast = Continue()
        return node

    def transform_TryStatement(self, node, metadata):
        if not hasattr(node, 'finalizer') or node.finalizer == None:
            finalbody = []
        else:
            finalbody = node.finalizer.python_ast

        if not hasattr(node, 'handler') or node.handler == None:
            handler = [Pass()]
        else:
            handler = [node.handler.python_ast]

        if not hasattr(node, 'block') or node.block == None:
            block = [Pass()]
        else:
            block = node.block.python_ast

        node.python_ast = Try(body=block, handlers=handler,
                              finalbody=finalbody, orelse=[])
        return node

    def transform_CatchClause(self, node, metadata):
        node.python_ast = ExceptHandler(type=None, body=node.body.python_ast, name=node.param.python_ast.id)
        return node

    def transform_BinaryExpression(self, node, metadata):
        if not node.right.elements:
            node.right.elements = []
        mapping = {
            'instanceof': Call(func=Name(id='isinstance', ctx=Load()),
                               args=[node.left.python_ast, node.right.python_ast], keywords=[]),
            'in': Compare(left=node.left.python_ast, ops=[In()],
                          comparators=[el.python_ast for el in node.right.elements]),
            '+': BinOp(left=node.left.python_ast, op=Add(), right=node.right.python_ast),
            '-': BinOp(left=node.left.python_ast, op=Sub(), right=node.right.python_ast),
            '*': BinOp(left=node.left.python_ast, op=Mult(), right=node.right.python_ast),
            '/': BinOp(left=node.left.python_ast, op=Div(), right=node.right.python_ast),
            '%': BinOp(left=node.left.python_ast, op=Mod(), right=node.right.python_ast),
            '**': BinOp(left=node.left.python_ast, op=Pow(), right=node.right.python_ast),
            '|': BinOp(left=node.left.python_ast, op=BitOr(), right=node.right.python_ast),
            '^': BinOp(left=node.left.python_ast, op=BitXor(), right=node.right.python_ast),
            '&': BinOp(left=node.left.python_ast, op=BitAnd(), right=node.right.python_ast),
            '==': BinOp(left=node.left.python_ast, op=Eq(), right=node.right.python_ast),
            '!=': BinOp(left=node.left.python_ast, op=NotEq(), right=node.right.python_ast),
            '===': BinOp(left=node.left.python_ast, op=Eq(), right=node.right.python_ast),
            '!==': BinOp(left=node.left.python_ast, op=NotEq(), right=node.right.python_ast),
            '<': BinOp(left=node.left.python_ast, op=Lt(), right=node.right.python_ast),
            '>': BinOp(left=node.left.python_ast, op=Gt(), right=node.right.python_ast),
            '<=': BinOp(left=node.left.python_ast, op=LtE(), right=node.right.python_ast),
            '<<': BinOp(left=node.left.python_ast, op=LShift(), right=node.right.python_ast),
            '>>': BinOp(left=node.left.python_ast, op=RShift(), right=node.right.python_ast),
            '>>>': BinOp(left=node.left.python_ast, op=RShift(), right=node.right.python_ast),
            '||': BinOp(left=node.left.python_ast, op=Or(), right=node.right.python_ast),
            '>=': BinOp(left=node.left.python_ast, op=GtE(), right=node.right.python_ast),
            '<=': BinOp(left=node.left.python_ast, op=LtE(), right=node.right.python_ast),
            '&&': BinOp(left=node.left.python_ast, op=And(), right=node.right.python_ast),
            '||': BinOp(left=node.left.python_ast, op=Or(), right=node.right.python_ast)
        }
        node.python_ast = mapping[node.operator]
        if not isinstance(node.python_ast, Call) and hasattr(node.python_ast, 'right') and isinstance(
                node.python_ast.right, Expr) and isinstance(node.python_ast.right.value, Num):
            node.python_ast.right = node.python_ast.right.value
        else:
            pass
        return node

def js2py(data, ret='code'):
    lines = data.splitlines()
    visitor = MyVisitor()
    visitor.lines = lines
    tree = esprima.parseScript(data, {'tolerant': True}, delegate=visitor)
    if ret == 'code':
        return astor.to_source(tree.python_ast)
    else:
        return tree.python_ast

if __name__ == "__main__":
    files = glob.glob("../../three.py/three.js/src/math/Matrix4.js")
    print(files)
    for fname in files:
        data = open(fname, 'r').read()
        print("################### {} ###################".format(fname))
        src = js2py(data)
        print(src)
#     tree = transpile_str("""
#     switch (foo)
#     {
#         case 1:
#             a();
#             b();
#         case 2:
#         case 3:
#             c();
#     }
#     """)
# #    print(tree)
#     print(astor.to_source(tree.python_ast))
