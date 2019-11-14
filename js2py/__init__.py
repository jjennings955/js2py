from collections import defaultdict

import astor
import pprint
import glob
import distutils.dir_util
import os
import pprint
import esprima
import ast
from ast import *

# from _ast.boolop import BoolOp
# from _ast.excepthandler import ExceptHandler
# from _ast.expr import Expr
# from _ast.mod import Mod
# from _ast.unaryop import UnaryOp
from esprima.visitor import ToDictVisitor

def ensure_list(l):
    if isinstance(l, list):
        return l
    else:
        return [l]

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
        self._nodemap = defaultdict(list)

    level = 0
    anon_cnt = 0

    def store(f):
        def thing(self, node, metadata):
            res = f(self, node, metadata)
            if not res:
                return res
            if isinstance(res, list):
                for r in res:
                    #r.python_ast._code = astor.to_source(r.python_ast)
                    self._nodemap[r.python_ast.__class__.__name__].append(r.python_ast)
            else:
                if not isinstance(res.python_ast, list):
                    pass
                    #res.python_ast._code = astor.to_source(res.python_ast)
                self._nodemap[res.python_ast.__class__.__name__].append(res.python_ast)

            return res
        return thing
    
    @store
    def transform_StaticMemberExpression(self, node, metadata):
        l = node.object.python_ast
        r = node.property.python_ast

        if node.computed:
            node.python_string = ("{a}[{b}]".format(a=l, b=r))
            node.python_ast = Subscript(value=l, slice=Index(value=r, ctx=Load()))
        else:
            node.python_string = ("{a}.{b}".format(a=l, b=r))

            node.python_ast = Attribute(value=l.value if isinstance(l, Expr) else l, attr=r.id, ctx=Load())
        return node

    @store
    def transform_MemberExpression(self, node, metadata):
        l = node.object.python_ast
        r = node.property.python_ast
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

    @store
    def transform_ExportDefaultDeclaration(self, node, params):
        node.python_ast = None
        return node

    @store
    def transform_FunctionExpression(self, node, params):
        return self.transform_FunctionDeclaration(node, params)

    @store
    def transform_ImportDeclaration(self, node, params):
        # import foo => Import(names=[alias(name='foo', asname=None)
        # import foo.bar => Import(names=[alias(name='foo.bar', asname=None)])
        # from foo import bar => ImportFrom(module='foo', names=[alias(name='bar', asname=None)], level=0)
        # from foo import * => ImportFrom(module='foo', names=[alias(name='*', asname=None)], level=0)
        # from foo.bar import bar => ImportFrom(module='foo', names=[alias(name='bar', asname=None)], level=0)
        # from foo.bar import * => ImportFrom(module='foo.bar', names=[alias(name='*', asname=None)], level=0)
        # from foo.bar import a, b, c => ImportFrom(module='foo.bar', names=[alias(name='a', asname=None), alias(name='b', asname=None), alias(name='c', asname=None)], level=0)

        try:
            if len(node.specifiers) < 0:
                if node.specifiers[0].imported.python_ast == node.specifiers[0].local.python_ast:
                    node.python_ast = Import(names=[alias(name=node.specifiers[0].imported.python_ast, asname=None)])
                    return node
            elif len(node.specifiers) >= 0:
                names = []
                for spec in node.specifiers:
                    if hasattr(spec, 'imported') and spec.imported == None:
                        names.append(alias(name='*', asname=spec.local.name))
                    else:
                        names.append(alias(name=spec.imported.name, asname=None if spec.local.name == spec.imported.name else spec.local.name))
                node.python_ast = ImportFrom(module=node.source.python_ast.s, names=names, level=0)
            else:
                node.python_ast = ImportFrom(module=node.source.python_ast.s,
                                         names=[alias(name=imp.imported.name,
                                                      asname=imp.local.name if (hasattr(imp, 'local') and hasattr(imp.local, 'name') and hasattr(imp, 'imported') and hasattr(imp.imported, 'name') and imp.local.name != imp.imported.name) else None) for imp in node.specifiers ], level=0)
        except Exception as e:
            node.python_ast = Import(names=[alias(name='ImportFailure', asname=None)])

        return node

    @store
    def transform_MetaProperty(self, node, params):
        node.python_ast = Pass()
        return node

    @store
    def transform_ThisExpression(self, node, params):
        node.python_ast = Name(id='self', ctx=Load())
        return node

    @store
    def transform_ReturnStatement(self, node, params):
        if node.argument and node.argument.python_ast:
            node.python_ast = Return(value=node.argument.python_ast)
        else:
            node.python_ast = Return(value=NameConstant(value=None))
        return node

    @store
    def transform_BlockStatement(self, node, params):
        if not len(node.body):
            node.python_ast = [Pass()]
        else:
            node.python_ast = unroll_body([child.python_ast for child in node.body])
        return node

    @store
    def transform_ThrowStatement(self, node, params):
        if astor.to_source(node.argument.python_ast.func).rstrip() == 'Error':
            node.argument.python_ast.func.id = 'Exception'
        node.python_ast = Raise(exc=Call(func=node.argument.python_ast.func, args=[n.python_ast for n in node.argument.arguments], keywords=[]), cause=None)
        return node

    @store
    def transform_AnonymousFunction(self, node, params):
        node.python_ast = Name(id="Anonymous" + "_" + str(self.anon_cnt), ctx=Load())
        if not isinstance(node.body.python_ast, list):
            node.body.python_ast = [node.body.python_ast]
        num = len(node.body.python_ast)
        if num == 0:
            node.body.python_ast = [Pass()]
        elif node.type == 'ArrowFunctionExpression' and not (isinstance(node.body.python_ast[num - 1], Return) or isinstance(node.body.python_ast[num - 1], Pass)  or isinstance(node.body.python_ast[num - 1], Yield)):
            node.body.python_ast[num - 1] = Return(node.body.python_ast[num - 1])
        #node.body.python_ast[num - 1] = Return(value=node.body.python_ast[num - 1])
        self._funcs["Anonymous" + "_" + str(self.anon_cnt)] = FunctionDef(
            name="Anonymous" + "_" + str(self.anon_cnt),
            args=arguments(args=[arg(arg=argument.name, annotation=None) for argument in
                                 node.params], vararg=None, kwonlyargs=[], kw_defaults=[],
                           kwarg=None, defaults=[]),
            body=unroll_body(node.body.python_ast),
            decorator_list=[], returns=None)
        #self.node = Name(
        self.anon_cnt += 1
        return node

    @store
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

    @store
    def transform_AssignmentExpression(self, node, metadata):
        node.left.python_ast.ctx = Store()
        if node.operator in ['+=', '++', '-=', '--']:
            return self.transform_UpdateExpression(node, metadata)
        try:
            source_left = astor.to_source(node.left.python_ast).strip()
            source_right = astor.to_source(node.right.python_ast).strip()
            # # TODO: Refactor
            # if source_left.endswith('.prototype'):
            #     class_name = node.left.python_ast.value.id
            #     if class_name not in self._classes:
            #         class_obj = ClassDef(name=class_name, bases=[], decorator_list=[])
            #         class_obj.body = []
            #     if source_right.startswith('Object.assign(Object.create('):
            #         for i, key in enumerate(node.right.python_ast.args[1].keys):
            #             real_name = key.id
            #             rhs = node.right.python_ast.args[1].values[i]
            #             if isinstance(rhs, Name):
            #                 placeholder_name = rhs.id
            #                 anon = self._funcs[placeholder_name]
            #                 if real_name == 'constructor':
            #                     real_name = '__init__'
            #
            #
            #                 anon.name = real_name
            #                 anon.args.args.insert(0, arg(arg='self', annotation=None))
            #                 class_obj.body.append(anon)
            #                 class_obj.body = unroll_body(class_obj.body)
            #     else:
            #         pass
            #
            #     self._classes[class_name] = class_obj
            #     node.python_ast = []
            #     return node
            # # TODO: Refactor
            # elif '.prototype.' in source_left and isinstance(node.right.python_ast, Name):
            #     tokens = source_left.split('.')
            #     class_name = tokens[0]
            #     if class_name in self._classes:
            #         func_name = source_right
            #         fun = self._funcs.get(func_name, node.right.python_ast.id)
            #         if fun.name == class_name:
            #             fun.name = "__init__"
            #         else:
            #             fun.name = tokens[-1]
            #
            #         fun.args.args.insert(0, arg(arg='self', annotation=None))
            #         self._classes[class_name].body.append(fun)
            #
            #         self._classes[class_name].body = unroll_body(self._classes[class_name].body)
            #         node.python_ast = []
            #         return node


        except (AttributeError, IndexError) as e:
            pass
        node.python_ast = Assign(targets=[node.left.python_ast], value=node.right.python_ast, ctx=Load())

        return node

    @store
    def transform_Literal(self, node, metadata):
        node.python_string = repr(node.value)
        if node.raw == 'null':
            node.python_ast = NameConstant(value=None)
        if isinstance(node.value, int) or isinstance(node.value, float):
            node.python_ast = Num(n=node.value)
        if isinstance(node.value, str):
            node.python_ast = Str(s=node.value)

        return node

    @store
    def transform_RegexLiteral(self, node, metadata):
        node.python_ast = ast.parse(str(node.value)).body[0].value
        return node

    @store
    def transform_NewExpression(self, node, metadata):
        return self.transform_CallExpression(node, metadata)

    @store
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
        # src = astor.to_source(node.callee.python_ast)
        # if src.startswith("QUnit."):
        #     test_name = node.python_ast.args[0].s
        #     test_func = node.python_ast.args[1].id
        #     func = self._funcs.pop(test_func)
        #     func.name = "test_" + test_name
        #     node.python_ast = func
        # # TODO: Refactor
        # if src.startswith("Object.assign(") and not src.startswith("Object.assign(Object.create"):
        #     if isinstance(node.python_ast.args[0], Attribute):
        #         class_name = node.python_ast.args[0].value.id
        #     elif isinstance(node.python_ast.args[0], Name):
        #         class_name = node.python_ast.args[0].id
        #     else:
        #         pass
        #         #print(ast.dump(node.python_ast.args))
        #
        #     class_obj = self._classes.get(class_name, ClassDef(name=class_name, bases=[], decorator_list=[], body=[]))
        #     self._classes[class_name] = class_obj
        #
        #     for i, key in enumerate(node.python_ast.args[1].keys):
        #         real_name = key.id
        #         rhs = node.python_ast.args[1].values[i]
        #         if isinstance(rhs, Name):
        #             placeholder_name = rhs.id
        #             anon = self._funcs[placeholder_name]
        #             if real_name == 'constructor':
        #                 real_name = '__init__'
        #             #self._funcs[placeholder_name].python_ast = None
        #             del self._funcs[placeholder_name]
        #
        #             anon.name = real_name
        #
        #             anon.args.args.insert(0, arg(arg='self', annotation=None))
        #             class_obj.body.append(anon)
        #             class_obj.body = unroll_body(class_obj.body)
        #     node.python_ast = Pass()

        return node

    @store
    def transform_Identifier(self, node, metadata):
        if node.name == 'undefined':
            node.python_string = 'None'
            node.python_ast = NameConstant(value=None)
        else:
            node.python_ast = Name(id=node.name, ctx=Load())
        return node

    @store
    def transform_ArrayExpression(self, node, metadata):
        elements = []
        for child in node.elements:
            elements.append(child.python_ast)
        node.python_ast = List(elts=elements, ctx=Load())
        return node

    @store
    def transform_Property(self, node, metadata):
        node.python_ast = Attribute(value=node.key.python_ast, attr=node.value.python_ast, ctx=Load())
        return node

    @store
    def transform_ObjectExpression(self, node, metadata):
        keys = []
        vals = []
        for prop in node.properties:
            keys.append(prop.key.python_ast)
            vals.append(prop.value.python_ast)
        node.python_ast = Dict(keys=keys, values=vals)
        return node

    @store
    def transform_Program(self, node, metadata):
        body = []
        for func in list(self._funcs.keys()):
            if func in self._classes:
                _func = self._funcs.pop(func)
                _func.name = '__init__'

                self._classes[func].body.insert(0, _func)

        body.extend(list(self._classes.values()))
        body.extend(list(self._funcs.values()))
        body.extend(unroll_body(n.python_ast for n in node.body if n != None))

        node.python_ast = Module(body=body)
        return node

    @store
    def transform_ExpressionStatement(self, node, metadata):
        if isinstance(node.expression.python_ast, Assign):
            node.python_ast = node.expression.python_ast
        else:
            node.python_ast = Expr(value=node.expression.python_ast)

        return node

    @store
    def transform_VariableDeclarator(self, node, metadata):
        if node.init:
            node.python_ast = Assign(targets=[Name(id=node.id.name, ctx=Store())], value=node.init.python_ast)
        else:
            node.python_ast = Assign(targets=[Name(id=node.id.name, ctx=Store())], value=NameConstant(value=None))
        return node

    @store
    def transform_VariableDeclaration(self, node, metadata):
        node.python_ast = [n.python_ast for n in node.declarations]
        return node

    @store
    def transform_IfStatement(self, node, metadata):
        if not isinstance(node.consequent.python_ast, list):
            body = [node.consequent.python_ast]
        else:
            body = node.consequent.python_ast
        node.python_ast = If(test=node.test.python_ast, body=unroll_body(body), orelse=ensure_list(node.alternate.python_ast) if node.alternate else [])

        return node

    @store
    def transform_ForInStatement(self, node, metadata):
        node.python_ast = For(target=Name(id=node.left.name, ctx=Store()),
                              iter=node.right.python_ast,
                              body=unroll_body(node.body.python_ast),
                              orelse=[])

        return node

    @store
    def transform_ForOfStatement(self, node, metadata):
        return self.transform_ForInStatement(node, metadata)

    @store
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

        node.python_ast.append(While(test=test_ast, body=unroll_body([body_ast] + ([node.update.python_ast] if node.update else [])), orelse=[]))
        if len(node.python_ast) == 1:
            node.python_ast = node.python_ast[0]
        else:
            node.python_ast = unroll_body(node.python_ast)
        return node

    @store
    def transform_WhileStatement(self, node, metadata):
        node.python_ast = While(
            test=node.test.python_ast,
            body=unroll_body(node.body.python_ast), orelse=[])

        return node

    @store
    def transform_EmptyStatement(self, obj, metadata):
        obj.python_ast = None
        return obj

    @store
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

    @store
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

        if node.operator in ['+', '-', '~', '!']:
            node.python_ast = UnaryOp(op=new_op(), operand=node.argument.python_ast)
        elif new_op == Delete:
            node.python_ast = Delete(targets=[node.argument.python_ast])
        else:
            node.python_ast = node.argument.python_ast

        return node

    @store
    def transform_LogicalExpression(self, obj, metadata):
        if obj.operator == '||':
            obj.python_ast = BinOp(left=obj.left.python_ast, op=Or(), right=obj.right.python_ast)
        if obj.operator == '&&':
            obj.python_ast = BinOp(left=obj.left.python_ast, op=And(), right=obj.right.python_ast)

        return obj

    @store
    def transform_ConditionalExpression(self, node, metadata):
        node.python_ast = IfExp(test=node.test.python_ast, body=node.consequent.python_ast,
                                orelse=node.alternate.python_ast)
        return node

    @store
    def transform_YieldExpression(self, node, metadata):
        node.python_ast = Yield(value=node.argument.python_ast, ctx=Load())
        return node

    @store
    def transform_SequenceExpression(self, node, metadata):

        node.python_ast = [child.python_ast for child in node.expressions]
        return node

    @store
    def transform_BreakStatement(self, node, metadata):

        node.python_ast = Break()
        return node

    @store
    def transform_SwitchStatement(self, node, metadata):
        node.python_ast = [c.python_ast for c in node.cases if c.test]
        default = [c.python_ast.body for c in node.cases if not c.test]
        for n in node.python_ast:
            n.test = BoolOp(op=Eq(), values=[node.discriminant.python_ast, n.test])
        def merge(n, rest):
            j = 0
            if not n.body:
                n.test = BoolOp(op=Or(), values=[n.test, rest[j].test])
                n.body = rest[j].body
                j += 1

            if len(rest) > j:
                n.orelse = [merge(rest[j], rest[j + 1:])]
                return n
            elif len(rest) == j+1:
                n.orelse = [rest[j]]
                return n
            else:
                # if default:
                #     default[0].test = NameConstant(value=True)
                n.orelse = []
                return n

        node.python_ast = [merge(node.python_ast[0], node.python_ast[1:])]
        if default:
            node.python_ast.extend(default[0])
        return node

    @store
    def transform_ArrowFunctionExpression(self, node, metadata):
        return self.transform_FunctionDeclaration(node, metadata)

    @store
    def transform_ClassDeclaration(self, node, metadata):
        class_obj = ClassDef(name=node.id.name, bases=[], decorator_list=[])
        class_obj.body = []
        if len(node.body.python_ast) > 0:
            for meth in node.body.python_ast:
                class_obj.body.append(meth)
        else:
            class_obj.body = [Pass()]
        self._classes[node.id.name] = class_obj
        node.python_ast = None
        return node

    @store
    def transform_ClassBody(self, node, metadata):
        node.python_ast = [n.python_ast for n in node.body]
        return node

    @store
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

    @store
    def transform_SwitchCase(self, node, metadata):
        test = node.test.python_ast if hasattr(node.test, 'python_ast') else []
        node.python_ast = If(test=test, body=[c.python_ast for c in node.consequent], orelse=[])
        return node

    @store
    def transform_ContinueStatement(self, node, metadata):
        node.python_ast = Continue()
        return node

    @store
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

    @store
    def transform_CatchClause(self, node, metadata):
        exception_type = Name(id='Exception', ctx=Load())
        node.python_ast = ExceptHandler(type=exception_type, body=node.body.python_ast, name=node.param.python_ast.id)
        return node

    @store
    def transform_BinaryExpression(self, node, metadata):
        if not node.right.elements:
            node.right.elements = []
        mapping = {
            'instanceof': Call(func=Name(id='isinstance', ctx=Load()),
                               args=[node.left.python_ast, node.right.python_ast], keywords=[]),
            'in': Compare(ctx=Load(), left=node.left.python_ast, ops=[In()],
                          comparators=[List(elts=[el.python_ast for el in node.right.elements])]
                          if len(node.right.elements) > 1
                          else [node.right.python_ast]),
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

def _(node):
    return astor.to_source(node).rstrip()

def _d(node):
    return ast.dump(node)
def handle_Object_assign(visitor, node):
    source_left = astor.to_source(node.left.python_ast).strip()
    source_right = astor.to_source(node.right.python_ast).strip()
    # # TODO: Refactor
    # if source_left.endswith('.prototype'):
    #     class_name = node.left.python_ast.value.id
    #     if class_name not in self._classes:
    #         class_obj = ClassDef(name=class_name, bases=[], decorator_list=[])
    #         class_obj.body = []
    #     if source_right.startswith('Object.assign(Object.create('):
    #         for i, key in enumerate(node.right.python_ast.args[1].keys):
    #             real_name = key.id
    #             rhs = node.right.python_ast.args[1].values[i]
    #             if isinstance(rhs, Name):
    #                 placeholder_name = rhs.id
    #                 anon = self._funcs[placeholder_name]
    #                 if real_name == 'constructor':
    #                     real_name = '__init__'
    #
    #
    #                 anon.name = real_name
    #                 anon.args.args.insert(0, arg(arg='self', annotation=None))
    #                 class_obj.body.append(anon)
    #                 class_obj.body = unroll_body(class_obj.body)
    #     else:
    #         pass
    #
    #     self._classes[class_name] = class_obj
    #     node.python_ast = []
    #     return node

def post_process(visitor):
    for thing in visitor._nodemap['Call']:
        #print(ast.dump(thing))
        func_name = astor.to_source(thing.func).strip()
        foo = { i : astor.to_source(getattr(thing, i)).rstrip() if not isinstance(getattr(thing, i), list) else '\n'.join(astor.to_source(j) for j in getattr(thing, i)).rstrip() for i in thing._fields }
        print(func_name)
        if func_name == 'Object.assign':
            arg1 = _(thing.args[0])
            if arg1.startswith("Object.create"):
                # Extract class w/ superclass
                pass
            if arg1.endswith(".prototype"):
                # extract class with no superclass
                pass
            #print(_(thing))

        if func_name == "Object.defineProperty":
            # extract a single class method/property
            pass
            #print(_(thing))

        if func_name == "Object.defineProperties":
            # extract class definition from properties dict
            pass
            #print(_(thing))

        if func_name.startswith("QUnit.module"):
            # extract all tests for module
            pass

        # if func_name.startswith("QUnit.test"):
        #     pass


        if func_name.startswith("Array."):
            print(_d(thing))

        if func_name.endswith(".push"):
            #print((thing.func.attr))
            if len(thing.args) == 1:
                thing.func.attr = 'append'
            else:
                thing.func.attr = 'extend'
                thing.func.args = List(elts=thing.args)

        if func_name.startswith("Array."):
            print(_(thing))
        if func_name.startswith("WeakMap."):
            print(_(thing))

         #   print(_d(thing))
        #    print(_(thing))
        if func_name == "Object.keys":
            thing.func.value.id = thing.args[0]
            thing.args = []
            #print(_(thing))
            #print(_d(thing))
        for i, thing in enumerate(visitor._nodemap['Attribute']):
            #print(_d(thing))
            foo = thing
            attr = _(thing).strip()
            if attr.endswith(".length"):
               # print(_d(thing))
                thing = Call(func=Name(id='len', ctx=Load()), args=[thing.value])
                #print(_d(thing))
                #print(_d(foo))

            #print(thing.func.args[0])

def markup(x, parent=None, n=0):
    print("FOO", x)
    #print('\t'*n, isinstance(newt.body, list))
    if isinstance(x, list):
        out = [markup(k, x, n+1) for k in x if isinstance(k, AST)]
        for field in x:
            print("OI", field, isinstance(field, AST))
            if isinstance(field, AST):
                field.jason_parent = parent
        return out
    elif isinstance(x, AST):
        print(type(x))
        items = [markup(field, x, n+1) for k,field in x.__dict__.items()]
        print(items)
        for k, field in list(x.__dict__.items()):
            print("OI2", field, isinstance(field, AST))
            if isinstance(field, AST):
                field.jason_parent = x
                field.field_name = k
        return x

def js2py(data, ret='code', postprocess=None):
    lines = data.splitlines()
    visitor = MyVisitor()
    visitor.lines = lines
    tree = esprima.parseScript(data, {'tolerant': True}, delegate=visitor)
    if postprocess:
        tree = markup(tree)
        tree = post_process(visitor)
    if ret == 'code':
        return astor.to_source(tree.python_ast)
    elif ret == 'visitor':
        return visitor
    else:
        return tree.python_ast

if __name__ == "__main__":
    g = glob.glob("../data/three.js/src/core/Object3D.js")
    with open(g[0], 'r') as fd:
        tree = js2py(fd.read(), ret='other')
        newt = markup(tree)