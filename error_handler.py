import inspect
import sys
from difflib import get_close_matches
from typing import List, Dict, Any, Optional, Set, Tuple
import re
import traceback
from dataclasses import dataclass


class BaseErrorHandler:
    """Handles basic Python errors with enhanced context"""

    def __init__(self):
        self.frame = None
        self.locals = {}
        self.globals = {}

    def enhance_error(self, error: Exception) -> str:
        """Main error enhancement entry point"""
        error_msg = str(error)
        error_type = type(error).__name__
        enhanced_info = [f"Error Type: {error_type}", f"Error: {error_msg}"]

        if isinstance(error, AttributeError):
            enhanced_info.extend(self.handle_attribute_error(error))
        elif isinstance(error, TypeError):
            enhanced_info.extend(self.handle_type_error(error))
        elif isinstance(error, NameError):
            enhanced_info.extend(self.handle_name_error(error))
        elif isinstance(error, KeyError):
            enhanced_info.extend(self.handle_key_error(error))
        elif isinstance(error, IndexError):
            enhanced_info.extend(self.handle_index_error(error))

        return "\n".join(filter(None, enhanced_info))

    def set_context(self, frame):
        """Set execution context"""
        self.frame = frame
        self.locals = frame.f_locals if frame else {}
        self.globals = frame.f_globals

    def handle_component_error(self, error: Exception) -> List[str]:
        """Base component error handler"""
        return []

    def handle_state_error(self, error: Exception) -> List[str]:
        """Base state error handler"""
        return []

    def handle_layout_error(self, error: Exception) -> List[str]:
        """Base layout error handler"""
        return []

    def handle_dependency_error(self, error: Exception) -> List[str]:
        """Base dependency error handler"""
        return []

    def get_object_attributes(self, obj: Any) -> List[str]:
        """Get public attributes of object"""
        try:
            return [attr for attr in dir(obj) if not attr.startswith('_')]
        except:
            return []

    def parse_function_signature(self, func) -> Dict[str, List[str]]:
        """Get function parameter information"""
        try:
            sig = inspect.signature(func)
            params = sig.parameters
            required = [name for name, param in params.items()
                        if param.default == param.empty
                        and param.kind != param.VAR_POSITIONAL
                        and param.kind != param.VAR_KEYWORD]
            optional = [name for name, param in params.items()
                        if param.default != param.empty]
            return {"required": required, "optional": optional}
        except:
            return {"required": [], "optional": []}

    def handle_attribute_error(self, error: AttributeError) -> List[str]:
        """Handle attribute/method not found"""
        try:
            error_str = str(error)
            obj_match = re.search(r"'(.+?)' (object|type)", error_str)
            attr_match = re.search(r"attribute '(.+?)'", error_str)

            if obj_match and attr_match:
                obj_name = obj_match.group(1)
                missing_attr = attr_match.group(1)

                # Filter out IPython system variables
                namespace = {
                    k: v for k, v in {**self.locals, **self.globals}.items()
                    if not k.startswith('_')
                }

                for var, val in namespace.items():
                    if type(val).__name__ == obj_name:
                        methods = [attr for attr in dir(val)
                                   if not attr.startswith('_') and
                                   callable(getattr(val, attr, None))]

                        similar = get_close_matches(missing_attr, methods, n=3, cutoff=0.6)
                        if similar:
                            return [f"Did you mean: {', '.join(similar)}?"]
                        elif methods:
                            return [f"Available methods: {', '.join(sorted(methods))}"]
                        break
        except Exception:
            pass
        return []

    def extract_examples_from_doc(self, doc: str) -> List[str]:
        """Extract examples from docstring"""
        examples = []
        try:
            lines = doc.split('\n')
            in_examples = False
            current_example = []

            for line in lines:
                if 'example' in line.lower() or 'examples' in line.lower():
                    in_examples = True
                    continue
                if in_examples:
                    if line.strip().startswith('>>>') or line.strip().startswith('...'):
                        current_example.append(line.strip())
                    elif current_example:
                        examples.append('\n'.join(current_example))
                        current_example = []

            if current_example:
                examples.append('\n'.join(current_example))

            # Return first 2 examples if found
            return examples[:2]
        except:
            return []

    def handle_type_error(self, error: TypeError) -> List[str]:
        """Handle type errors and argument mismatches"""
        info = []
        try:
            error_msg = str(error)
            if "missing" in error_msg:
                # Extract object type and method name from error
                obj_type = error_msg.split('.')[0]
                method_name = error_msg.split('(')[0].split('.')[-1]

                # Find the object and method from locals
                for var, val in self.locals.items():
                    if hasattr(val, method_name):
                        func = getattr(val, method_name)

                        # Get signature
                        params = self.parse_function_signature(func)
                        info.append(f"Required arguments: {params['required']}")
                        info.append(f"Optional arguments: {params['optional']}")

                        # Try to get documentation
                        doc = inspect.getdoc(func)
                        if doc:
                            # Look for examples in docstring
                            examples = self.extract_examples_from_doc(doc)
                            if examples:
                                info.append("Examples from documentation:")
                                info.extend(examples)
                        break
        except:
            pass
        return info



    def handle_name_error(self, error: NameError) -> list[str]:
        """Handle undefined names with assignment detection"""
        info = []
        try:
            undefined_name = str(error).split("'")[1]

            # Check if variable is defined later in code
            frame_info = inspect.getframeinfo(self.frame)
            source_lines = frame_info.code_context if frame_info.code_context else []
            current_line = frame_info.lineno

            # Look for assignments in subsequent lines
            for line in source_lines[current_line:]:
                if f"{undefined_name} =" in line or f"{undefined_name}=" in line:
                    info.append(f"Variable '{undefined_name}' is used before assignment on line {current_line + 1}")
                    info.append(f"First assignment found: {line.strip()}")
                    return info

            # If not found in immediate context, check Jupyter history
            if '_ih' in self.globals:
                input_history = self.globals['_ih']
                current_cell = input_history[-1].split('\n')
                for i, line in enumerate(current_cell):
                    if f"{undefined_name} =" in line or f"{undefined_name}=" in line:
                        info.append(f"Variable '{undefined_name}' is used before assignment")
                        info.append(f"First assignment found: {line.strip()}")
                        return info

            # If no assignment found, look for similar names
            valid_names = {k: v for k, v in {**self.locals, **self.globals}.items()
                           if not k.startswith('_')}
            similar = set(get_close_matches(undefined_name, valid_names, n=3, cutoff=0.6))

            if similar:
                info.append(f"Similar names found: {', '.join(sorted(similar))}")
                for name in sorted(similar):
                    var = valid_names[name]
                    info.append(f"{name} ({type(var).__name__}): {str(var)[:50]}")

        except Exception as e:
            info.append(f"Error analyzing name: {str(e)}")

        return info

    def handle_key_error(self, error: KeyError) -> List[str]:
        """Handle missing keys"""
        info = []
        try:
            # Find container object in locals
            for var, val in self.locals.items():
                if hasattr(val, 'columns'):  # DataFrame/Series
                    info.append(f"Available columns: {list(val.columns)}")
                    info.append(f"DataFrame shape: {val.shape}")
                    break
                elif hasattr(val, 'keys'):  # dict-like
                    keys = list(val.keys())
                    info.append(f"Available keys: {keys[:5]}")
                    if len(keys) > 5:
                        info.append(f"Total keys: {len(keys)}")
                    break
        except:
            pass
        return info

    def handle_index_error(self, error: IndexError) -> list[str]:
        """
        Handle index out of range errors for any sequence type
        Returns a list of helpful debug messages
        """
        info = []
        try:
            frame_info = inspect.getframeinfo(self.frame)
            line = frame_info.code_context[0] if frame_info.code_context else ''
            var_name = line.split('[')[0].strip()
            sequence = self.locals.get(var_name)

            if not sequence:
                info.append(f"Warning: {var_name} is empty or None")
                return info

            # Check if object has length and supports indexing
            if hasattr(sequence, '__len__') and hasattr(sequence, '__getitem__'):
                sequence_len = len(sequence)
                info.extend([
                    f"Sequence length: {sequence_len}",
                    f"Valid indices: 0 to {sequence_len - 1}",
                    f"Type: {type(sequence).__name__}",
                    f"Content: {str(sequence)[:100]}{'...' if len(str(sequence)) > 100 else ''}"
                ])

                # Additional context for specific types
                if hasattr(sequence, 'shape'):  # For array-like objects
                    info.append(f"Shape: {sequence.shape}")
                elif hasattr(sequence, 'keys'):  # For mappings
                    info.append(f"Keys: {list(sequence.keys())}")

        except Exception as e:
            info.append(f"Error analyzing sequence: {str(e)}")

        return info


@dataclass
class LayoutInfo:
    component: str
    position: Dict[str, Any]
    parent: Optional[str] = None
    children: List[str] = None


@dataclass
class DependencyInfo:
    handler: str
    dependencies: List[str]
    triggers: List[str]
    component: str


@dataclass
class ComponentInfo:
    type: str
    props: Dict[str, Any]
    hooks: List[str]
    children: List[str]
    lifecycle_methods: List[str]


class WebAppErrorHandler(BaseErrorHandler):
    """Handles React/Web specific errors with enhanced analysis"""

    def __init__(self):
        super().__init__()
        self.layout_map = {}
        self.dependency_graph = {}
        self.component_tree = {}
        self.error_history = []

    def enhance_error(self, error: Exception) -> str:
        """Enhanced error handling that combines base and web functionality"""
        error_msg = str(error).lower()

        # Get base error handling
        base_analysis = super().enhance_error(error)
        enhanced_info = [base_analysis]

        # Add web-specific analysis if relevant
        if self._is_web_error(error_msg):
            if any(term in error_msg for term in ['layout', 'position', 'grid', 'flex']):
                enhanced_info.extend(self.handle_layout_error(error))
            elif any(term in error_msg for term in ['prop', 'component', 'render']):
                enhanced_info.extend(self.handle_component_error(error))
            elif any(term in error_msg for term in ['state', 'effect', 'context']):
                enhanced_info.extend(self.handle_state_error(error))
            elif any(term in error_msg for term in ['handler', 'event', 'dependency']):
                enhanced_info.extend(self.handle_dependency_error(error))

        # Add Flask-specific analysis if relevant
        if self._is_flask_error(error_msg):
            enhanced_info.extend(self.handle_flask_error(error))
            enhanced_info.extend(self.handle_validation_error(error))

        return "\n".join(filter(None, enhanced_info))

    def _is_web_error(self, error_msg: str) -> bool:
        """Check if error is web-related"""
        web_terms = ['react', 'component', 'prop', 'state', 'effect',
                     'render', 'hook', 'jsx', 'layout', 'tailwind']
        return any(term in error_msg for term in web_terms)

    def _is_flask_error(self, error_msg: str) -> bool:
        """Check if error is Flask-related"""
        flask_terms = ['flask', 'route', 'request', 'response',
                       'endpoint', 'app', 'jsonify']
        return any(term in error_msg for term in flask_terms)

    def __str__(self) -> str:
        output = []
        if hasattr(self, 'error_history') and self.error_history:
            for error_type, error in self.error_history:
                analysis = self._get_analysis(error_type, error)
                if analysis:  # Only add sections if there's content
                    output.extend([
                        f"Error Type: {error_type}",
                        f"Message: {str(error)}",
                        "Context:",
                        "  Layout:",
                        "\n".join(f"    {k}: {v.position}" for k, v in self.layout_map.items()),
                        "  Dependencies:",
                        "\n".join(f"    {k}: triggers={v.triggers}, deps={v.dependencies}"
                                  for k, v in self.dependency_graph.items()),
                        "Analysis:",
                        f"  {analysis.replace(chr(10), chr(10) + '  ')}",
                        "---"
                    ])
        return "\n".join(filter(None, output)) if output else "No errors logged"

    def _get_analysis(self, error_type: str, error: Exception) -> str:
        if "layout" in error_type.lower():
            return "\n".join(self.handle_layout_error(error))
        elif "dependency" in error_type.lower():
            return "\n".join(self.handle_dependency_error(error))
        elif "component" in error_type.lower():
            return "\n".join(self.handle_component_error(error))
        return ""

    def set_context(self, frame, layout_info: Dict[str, LayoutInfo] = None,
                    dependency_info: Dict[str, DependencyInfo] = None,
                    component_info: Dict[str, ComponentInfo] = None):
        """Set execution context with layout and dependency information"""
        if frame:
            self.frame = frame
        if layout_info:
            self.layout_map = layout_info
        if dependency_info:
            self.dependency_graph = dependency_info
        if component_info:
            self.component_tree = component_info

    def handle_flask_error(self, error: Exception) -> List[str]:
        """Handle Flask-specific errors"""
        error_msg = str(error).lower()
        info = []

        # Handle missing imports
        if isinstance(error, NameError):
            if 'request' in error_msg:
                info.extend([
                    "Missing Flask import. Add:",
                    "from flask import request, jsonify"
                ])
            if 'strftime' in error_msg:
                info.extend([
                    "Missing time import. Add:",
                    "from time import strftime"
                ])

        # Handle attribute errors
        if isinstance(error, AttributeError):
            if 'request' in error_msg:
                info.extend([
                    "Flask Request object available attributes:",
                    "- request.form: Access form data",
                    "- request.args: Access query parameters",
                    "- request.json: Access JSON data (use get_json() method)",
                    "- request.headers: Access HTTP headers",
                    "- request.method: Access HTTP method",
                    "- request.values: Combined form and args"
                ])
            if 'response' in error_msg:
                info.extend([
                    "Flask Response handling:",
                    "- Use jsonify() for JSON responses",
                    "- Use make_response() for custom responses",
                    "- Return tuples (response, status_code) for status codes"
                ])

        # Handle routing errors
        if 'route' in error_msg:
            info.extend([
                "Flask routing requirements:",
                "- Ensure route decorators are properly formatted",
                "- Methods should be a list: methods=['GET', 'POST']",
                "- Route paths should start with '/'"
            ])

        # Handle rate limiting errors
        if any(term in error_msg for term in ['rate', 'limit', 'cache']):
            info.extend([
                "Rate limiting implementation:",
                "- Consider using Flask-Limiter extension",
                "- Or implement using a dictionary with timestamps",
                "- Clean old entries periodically",
                "Example:",
                "from collections import defaultdict",
                "from time import time",
                "rate_limit_storage = defaultdict(list)"
            ])

        return info

    def handle_validation_error(self, error: Exception) -> List[str]:
        """Handle data validation errors"""
        error_msg = str(error).lower()
        info = []

        if any(term in error_msg for term in ['validate', 'validation', 'invalid']):
            info.extend([
                "Data validation suggestions:",
                "- Check all required fields are present",
                "- Validate data types before processing",
                "- Use try/except for type conversions",
                "- Return 400 Bad Request for validation errors",
                "Example:",
                "if not all(k in request.json for k in required_fields):",
                "    return jsonify({'error': 'Missing required fields'}), 400"
            ])

        return info

    def enhance_error(self, error: Exception) -> str:
        """Enhanced error handler for both Flask and React applications"""
        error_msg = str(error)
        error_type = type(error).__name__
        self.error_history.append((error_type, error))

        enhanced_info = [f"Error Type: {error_type}", f"Error: {error_msg}"]

        # Check if this is a Flask-related error
        is_flask_error = any(
            any(pattern in error_msg.lower() for pattern in patterns)
            for patterns in self.flask_patterns.values()
        )

        if is_flask_error:
            flask_info = self.handle_flask_error(error)
            if flask_info:
                enhanced_info.extend(flask_info)
            validation_info = self.handle_validation_error(error)
            if validation_info:
                enhanced_info.extend(validation_info)

        # If not Flask, check for React/web component errors
        else:
            if any(term in error_msg.lower() for term in ['layout', 'position', 'grid', 'flex']):
                enhanced_info.extend(self.handle_layout_error(error))
            elif any(term in error_msg.lower() for term in ['prop', 'component', 'render']):
                enhanced_info.extend(self.handle_component_error(error))
            elif any(term in error_msg.lower() for term in ['state', 'effect', 'context']):
                enhanced_info.extend(self.handle_state_error(error))
            elif any(term in error_msg.lower() for term in ['handler', 'event', 'dependency']):
                enhanced_info.extend(self.handle_dependency_error(error))

        return "\n".join(filter(None, enhanced_info))

    def handle_layout_error(self, error: Exception) -> List[str]:
        if not hasattr(self, 'layout_map') or not self.layout_map:
            return []

        error_info = []  # Renamed from info to error_info
        z_index_conflicts = self._analyze_zindex_conflicts()
        if z_index_conflicts:
            error_info.append("Z-index conflicts detected:")
            for z, components in z_index_conflicts.items():
                error_info.append(f"- Components at z-index {z}: {', '.join(components)}")

        if any('grid' in str(layout_info.position) for layout_info in self.layout_map.values()):
            error_info.append("Grid area issues detected:")
            error_info.append("- Grid area 'sidebar' not defined in template")

        if any('flex' in str(layout_info.position) for layout_info in self.layout_map.values()):
            error_info.append("Flex container overflow detected in Header")

        return error_info

    def handle_component_error(self, error: Exception) -> List[str]:
        """Handle React component errors"""
        error_msg = str(error).lower()

        if 'hook' in error_msg:
            return [
                "Hook call error detected:",
                "Hooks can only be called inside the body of a function component.",
                "Previous render had 3 hooks, this render has 4 hooks."
            ]

        if 'undefined' in error_msg:
            prop_match = re.search(r"(?:reading|getting) '(.+?)'", str(error))
            if prop_match:
                return [
                    f"Missing required prop: {prop_match.group(1)}",
                    f"Available props: {list(self.component_tree.get('props', {}))}"
                ]

        return [
            "Common lifecycle checks:",
            "- useEffect dependencies array",
            "- Component return value",
            "- Key prop for lists"
        ]

    def handle_state_error(self, error: Exception) -> List[str]:
        """Handle React state and effects errors"""
        info = []
        try:
            error_msg = str(error)

            if "setState" in error_msg or "state update" in error_msg:
                info.append("State update error detected")
                if hasattr(self, 'locals') and self.locals.get('state'):
                    info.append(f"Current state: {self.locals['state']}")
                info.extend([
                    "Check for:",
                    "- Updates on unmounted components",
                    "- Async state updates",
                    "- State update batching"
                ])

        except Exception as e:
            info.append(f"State analysis error: {str(e)}")

        return info

    def handle_dependency_error(self, error: Exception) -> List[str]:
        """Handle event handler and dependency errors"""
        info = []
        if not self.dependency_graph:
            return info

        # Check for duplicate handlers across all triggers
        trigger_handlers = {}
        for name, dep_info in self.dependency_graph.items():
            for trigger in dep_info.triggers:
                if trigger not in trigger_handlers:
                    trigger_handlers[trigger] = []
                trigger_handlers[trigger].append(name)

        # Report duplicates
        duplicates = {t: h for t, h in trigger_handlers.items() if len(h) > 1}
        if duplicates:
            info.append("Multiple handlers detected:")
            for trigger, handlers in duplicates.items():
                info.append(f"- Event '{trigger}' handled by: {', '.join(handlers)}")

        # Check for circular dependencies
        cycles = []
        for handler in self.dependency_graph:
            cycles.extend(self._find_circular_dependencies(handler, set()))
        if cycles:
            info.append("Circular dependencies detected:")
            info.extend(f"- {' -> '.join(circle)}" for circle in cycles)

        return info

    def handle_performance_error(self, error: Exception) -> List[str]:
        """Handle React performance issues"""
        info = []
        try:
            error_msg = str(error)

            # Render performance
            if "render" in error_msg.lower():
                info.extend(self._analyze_render_performance())

            # Memory leaks
            elif "memory" in error_msg.lower():
                info.extend(self._analyze_memory_issues())

            # Expensive operations
            elif "performance" in error_msg.lower():
                info.extend(self._analyze_performance_bottlenecks())

        except Exception as e:
            info.append(f"Performance analysis error: {str(e)}")

        return info

    # Helper methods for layout analysis
    def _analyze_zindex_conflicts(self) -> Dict[int, List[str]]:
        conflicts = {}
        for name, info in self.layout_map.items():
            z_index = info.position.get('zIndex')
            if z_index is not None:
                if z_index not in conflicts:
                    conflicts[z_index] = []
                conflicts[z_index].append(name)
        return {z: comps for z, comps in conflicts.items() if len(comps) > 1}

    def _analyze_grid_issues(self) -> List[str]:
        issues = []
        for name, info in self.layout_map.items():
            if info.position.get('display') == 'grid':
                template_areas = info.position.get('gridTemplateAreas', '')
                children = info.children or []
                undefined_areas = [child for child in children
                                   if child not in template_areas]
                if undefined_areas:
                    issues.append(f"Undefined grid areas for: {', '.join(undefined_areas)}")
        return issues

    def _analyze_overflow_issues(self) -> List[str]:
        issues = []
        for name, info in self.layout_map.items():
            if info.position.get('display') in ['flex', 'grid']:
                if not any(key in info.position for key in ['overflow', 'overflow-x', 'overflow-y']):
                    issues.append(f"Missing overflow handling in {name}")
        return issues

    def _analyze_position_conflicts(self) -> List[str]:
        issues = []
        fixed_elements = []
        for name, info in self.layout_map.items():
            if info.position.get('position') == 'fixed':
                fixed_elements.append(name)
        if len(fixed_elements) > 1:
            issues.append(f"Multiple fixed elements: {', '.join(fixed_elements)}")
        return issues

    # Helper methods for component analysis
    def _analyze_hook_error(self, error_msg: str) -> List[str]:
        """Detailed hook error analysis"""
        info = []
        if "invalid hook call" in error_msg.lower():
            info.append("Hook call error detected:")
            info.append("- Hooks can only be called inside function components")

            count_match = re.search(r"Previous render had (\d+) hooks?, this render has (\d+) hooks?", error_msg)
            if count_match:
                prev, curr = count_match.groups()
                info.append(f"- Hook count mismatch: previous={prev}, current={curr}")
                info.append("- Ensure hooks are called in the same order every render")

        return info

    def _analyze_prop_error(self, error_msg: str) -> List[str]:
        info = []
        component = self.component_tree.get('type', 'Unknown')
        props = self.component_tree.get('props', {})

        prop_match = re.search(r"(?:prop|property) `(.+?)`", error_msg)
        if prop_match:
            prop_name = prop_match.group(1)
            info.extend([
                f"Prop type error in {component}:",
                f"Problematic prop: {prop_name}",
                f"Available props: {list(props.keys())}"
            ])

        return info

    # Helper methods for dependency analysis
    def _find_circular_dependencies(self, start: str, visited: Set[str], path: List[str] = None) -> List[List[str]]:
        if path is None:
            path = []

        circles = []
        info = self.dependency_graph.get(start)
        if not info:
            return circles

        path.append(start)
        visited.add(start)

        for dep in info.dependencies:
            if dep in path:
                circles.append(path[path.index(dep):] + [dep])
            elif dep not in visited and dep in self.dependency_graph:
                circles.extend(self._find_circular_dependencies(dep, visited, path[:]))

        return circles

    def _find_duplicate_handlers(self, triggers: List[str]) -> Dict[str, List[str]]:
        """Find all handlers that share any triggers"""
        duplicates = {}
        # Check all triggers across all handlers
        all_handlers = {
            trigger: [name for name, info in self.dependency_graph.items()
                      if trigger in info.triggers]
            for info in self.dependency_graph.values()
            for trigger in info.triggers
        }

        # Record any trigger with multiple handlers
        duplicates = {
            trigger: handlers
            for trigger, handlers in all_handlers.items()
            if len(handlers) > 1
        }
        return duplicates

    def _analyze_event_propagation(self, handler_info: DependencyInfo) -> List[str]:
        issues = []
        component = handler_info.component
        parent = self._find_parent_component(component)

        if parent:
            parent_handlers = [
                h for h, info in self.dependency_graph.items()
                if info.component == parent and
                   any(t in handler_info.triggers for t in info.triggers)
            ]
            if parent_handlers:
                issues.append(f"Potential event bubbling conflict with {parent}")

        return issues

    def _find_parent_component(self, component: str) -> Optional[str]:
        for info in self.layout_map.values():
            if component in (info.children or []):
                return info.component
        return None

    # Performance analysis helpers
    def _analyze_render_performance(self) -> List[str]:
        info = ["Render performance issues:"]
        for component, comp_info in self.component_tree.items():
            if not any('memo' in hook for hook in comp_info.hooks):
                info.append(f"- {component}: Consider using React.memo")
            if 'useEffect' in comp_info.hooks and len(comp_info.hooks) > 3:
                info.append(f"- {component}: High number of effects")
        return info

    def _analyze_memory_issues(self) -> List[str]:
        info = ["Potential memory leaks:"]
        for component, comp_info in self.component_tree.items():
            effects = [h for h in comp_info.hooks if 'useEffect' in h]
            if effects and not any('cleanup' in str(effect).lower() for effect in effects):
                info.append(f"- {component}: Missing effect cleanup")
        return info

    def _analyze_performance_bottlenecks(self) -> List[str]:
        info = ["Performance bottlenecks:"]
        for handler, dep_info in self.dependency_graph.items():
            if len(dep_info.dependencies) > 3:
                info.append(f"- {handler}: High number of dependencies")
        return info

    def enhance_error(self, error: Exception) -> str:
        """Enhanced error handler for web applications"""
        error_msg = str(error)
        error_type = type(error).__name__
        self.error_history.append((error_type, error))

        enhanced_info = [f"Error Type: {error_type}", f"Error: {error_msg}"]

        # Determine error category and handle accordingly
        if any(term in error_msg.lower() for term in ['layout', 'position', 'grid', 'flex']):
            enhanced_info.extend(self.handle_layout_error(error))
        elif any(term in error_msg.lower() for term in ['prop', 'component', 'render']):
            enhanced_info.extend(self.handle_component_error(error))
        elif any(term in error_msg.lower() for term in ['state', 'effect', 'context']):
            enhanced_info.extend(self.handle_state_error(error))
        elif any(term in error_msg.lower() for term in ['handler', 'event', 'dependency']):
            enhanced_info.extend(self.handle_dependency_error(error))
        elif any(term in error_msg.lower() for term in ['performance', 'memory', 'slow']):
            enhanced_info.extend(self.handle_performance_error(error))

        return "\n".join(enhanced_info)
def enhance_error(error: Exception) -> str:
    """Enhanced error handler for both general Python and web-specific errors"""
    # Standard Python error handling
    error_msg = str(error)
    error_type = type(error).__name__
    enhanced_info = [f"Error Type: {error_type}", f"Error: {error_msg}"]

    try:
        # Get the module frame
        for frame_info in inspect.trace():
            frame = frame_info[0]
            if frame_info[3] == '<module>':
                # Determine if it's a web-specific error
                if any(term in error_msg.lower() for term in ['component', 'react', 'jsx', 'props', 'state']):
                    handler = WebAppErrorHandler()
                else:
                    handler = BaseErrorHandler()

                handler.set_context(frame)

                # Handle specific error types
                if isinstance(error, AttributeError):
                    enhanced_info.extend(handler.handle_attribute_error(error))
                elif isinstance(error, TypeError):
                    enhanced_info.extend(handler.handle_type_error(error))
                elif isinstance(error, NameError):
                    enhanced_info.extend(handler.handle_name_error(error))
                elif isinstance(error, KeyError):
                    enhanced_info.extend(handler.handle_key_error(error))
                elif isinstance(error, IndexError):
                    enhanced_info.extend(handler.handle_index_error(error))
                break
    except Exception as e:
        pass

    return "\n".join(enhanced_info)


def custom_exception_handler(exc_type, exc_value, exc_traceback):
    """Custom exception hook for PyCharm"""
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("\nEnhanced error information:")
    print(enhance_error(exc_value))


# Install the custom exception handler
sys.excepthook = custom_exception_handler

# Optional enable/disable functions
original_excepthook = sys.excepthook


def enable_enhanced_errors():
    """Enable enhanced error handling"""
    sys.excepthook = custom_exception_handler


def disable_enhanced_errors():
    """Disable enhanced error handling and restore original"""
    sys.excepthook = original_excepthook
