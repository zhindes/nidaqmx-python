<%
import nidaqmx_python_generator.helpers as helpers

config = data['config']
functions = data['functions']
enums = data["enums"]
%>\

% for name, func_metadata in functions.items():
def ${name}():
    return ${helpers.function_return_type(func_metadata)}
% endfor
