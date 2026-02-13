import React from 'react';
import './ProcedureParameterInput.css';

interface Parameter {
    name: string;
    data_type: string;
    parameter_mode: 'IN' | 'OUT' | 'INOUT';
    ordinal_position: number;
    parameter_default?: string;
}

interface ProcedureParameterInputProps {
    parameters: Parameter[];
    values: Record<string, any>;
    onChange: (values: Record<string, any>) => void;
}

export const ProcedureParameterInput: React.FC<ProcedureParameterInputProps> = ({
    parameters,
    values,
    onChange
}) => {
    const handleChange = (paramName: string, value: any) => {
        onChange({
            ...values,
            [paramName]: value
        });
    };

    const getInputType = (dataType: string): string => {
        const type = dataType.toLowerCase();
        if (type.includes('int') || type.includes('numeric') || type.includes('decimal')) {
            return 'number';
        }
        if (type.includes('bool')) {
            return 'checkbox';
        }
        if (type.includes('date') && !type.includes('time')) {
            return 'date';
        }
        if (type.includes('timestamp') || type.includes('datetime')) {
            return 'datetime-local';
        }
        if (type.includes('time') && !type.includes('stamp')) {
            return 'time';
        }
        if (type.includes('json') || type.includes('text')) {
            return 'textarea';
        }
        return 'text';
    };

    const renderInput = (param: Parameter) => {
        const inputType = getInputType(param.data_type);
        const paramValue = values[param.name] ?? param.parameter_default ?? '';
        const isRequired = param.parameter_mode === 'IN' || param.parameter_mode === 'INOUT';

        if (inputType === 'checkbox') {
            return (
                <div className="checkbox-input">
                    <input
                        type="checkbox"
                        id={`param-${param.name}`}
                        checked={paramValue === true || paramValue === 'true'}
                        onChange={(e) => handleChange(param.name, e.target.checked)}
                    />
                    <label htmlFor={`param-${param.name}`}>
                        {paramValue ? 'True' : 'False'}
                    </label>
                </div>
            );
        }

        if (inputType === 'textarea') {
            return (
                <textarea
                    value={paramValue}
                    onChange={(e) => handleChange(param.name, e.target.value)}
                    placeholder={`Enter ${param.data_type} value`}
                    rows={4}
                    required={isRequired}
                />
            );
        }

        return (
            <input
                type={inputType}
                value={paramValue}
                onChange={(e) => {
                    const val = inputType === 'number' ?
                        (e.target.value ? Number(e.target.value) : '') :
                        e.target.value;
                    handleChange(param.name, val);
                }}
                placeholder={param.parameter_default || `Enter ${param.data_type} value`}
                required={isRequired}
            />
        );
    };

    if (parameters.length === 0) {
        return (
            <div className="no-parameters">
                <p>This procedure has no input parameters.</p>
            </div>
        );
    }

    // Sort by ordinal position
    const sortedParams = [...parameters].sort((a, b) => a.ordinal_position - b.ordinal_position);

    return (
        <div className="procedure-parameters">
            <h4>Procedure Parameters</h4>
            {sortedParams.map((param) => (
                <div key={param.name} className="parameter-group">
                    <label>
                        <span className="param-name">{param.name}</span>
                        <span className="param-type">{param.data_type}</span>
                        {param.parameter_mode !== 'IN' && (
                            <span className="param-mode">{param.parameter_mode}</span>
                        )}
                        {(param.parameter_mode === 'IN' || param.parameter_mode === 'INOUT') && (
                            <span className="required-indicator">*</span>
                        )}
                    </label>
                    {renderInput(param)}
                    {param.parameter_default && (
                        <small className="param-default">Default: {param.parameter_default}</small>
                    )}
                </div>
            ))}
        </div>
    );
};
