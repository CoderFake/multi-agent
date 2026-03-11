"use client";

import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";
import type { RJSFSchema, UiSchema, WidgetProps } from "@rjsf/utils";
import { Switch } from "@/components/ui/switch";
import { RichTextWidget } from "@/components/ui/rich-text-editor";

interface DynamicOptions {
    enum: (number | string)[];
    enumNames: string[];
}

interface DynamicToolFormProps {
    toolName: string;
    baseSchema: Record<string, unknown>;
    options: Record<string, DynamicOptions>;
    formData: Record<string, unknown>;
    onChange?: (formData: Record<string, unknown>) => void;
    onSubmit: (formData: Record<string, unknown>) => void;
    onCancel: () => void;
}

/**
 * Process the schema:
 * 1. Flatten anyOf (Pydantic Optional pattern) → plain type
 * 2. Remove field descriptions to avoid noisy labels
 * 3. Remove internal-only fields (form_meta)
 * 4. Detect date fields (format: "date") from json_schema_extra
 */
function processSchema(schema: RJSFSchema): RJSFSchema {
    if (!schema.properties) return schema;
    const props = schema.properties as Record<string, RJSFSchema>;
    const flatProps: Record<string, RJSFSchema> = {};

    const hiddenFields = new Set(["form_meta", "watcher_user_ids"]);

    for (const [key, prop] of Object.entries(props)) {
        if (hiddenFields.has(key)) continue;

        let resolved: RJSFSchema;

        if (Array.isArray(prop.anyOf)) {
            const nonNull = (prop.anyOf as RJSFSchema[]).filter((s) => s.type !== "null");
            if (nonNull.length === 1) {
                // Preserve root properties like format: "date", title, etc. which Pydantic puts outside anyOf
                resolved = { ...prop, ...nonNull[0], title: prop.title };
                delete resolved.anyOf;
            } else {
                resolved = { ...prop };
            }
        } else {
            resolved = { ...prop };
        }

        // Remove noisy descriptions
        delete resolved.description;

        flatProps[key] = resolved;
    }

    const required = (schema.required as string[] | undefined)?.filter((f) => !hiddenFields.has(f));
    return { ...schema, properties: flatProps, ...(required ? { required } : {}) };
}

/**
 * Inject dynamic enum options from API into the schema.
 * Preserves the original type (string for project_id, integer for ID fields).
 */
function mergeOptions(
    schema: RJSFSchema,
    options: Record<string, DynamicOptions>
): RJSFSchema {
    if (!schema.properties || !Object.keys(options).length) return schema;
    const props = { ...(schema.properties as Record<string, RJSFSchema>) };

    for (const [field, data] of Object.entries(options)) {
        if (props[field] && data.enum?.length) {
            // In RJSF v5/v6, enumNames is removed. Standard JSON Schema for labeled dropdowns uses oneOf.
            const originalProp = props[field] as any;
            const originalType = originalProp?.type || (typeof data.enum[0] === "string" ? "string" : "integer");
            const enumType = (originalType === "number" || originalType === "integer") ? "integer" : "string";

            const oneOfOptions = data.enum.map((val, index) => {
                const parsedVal = enumType === "integer" && typeof val === "string" ? parseInt(val, 10) : val;
                return {
                    const: parsedVal,
                    title: data.enumNames?.[index] ?? String(parsedVal)
                };
            });

            props[field] = {
                title: props[field].title,
                type: enumType,
                oneOf: oneOfOptions
            } as RJSFSchema;
        } else if (props[field] && (props[field] as any).dynamic_dropdown) {
        }
    }

    return { ...schema, properties: props };
}

/**
 * Build uiSchema:
 * - Dropdown widget for fields with enum options
 * - Date widget for fields with format: "date"
 * - Textarea for description
 */
function buildUiSchema(
    schema: RJSFSchema,
    options: Record<string, DynamicOptions>
): UiSchema {
    const ui: UiSchema = {
        "ui:submitButtonOptions": { norender: true },
    };

    if (!schema.properties) return ui;
    const props = schema.properties as Record<string, RJSFSchema>;

    for (const [key, prop] of Object.entries(props)) {
        let fieldUi: any = {};

        // 1. Extract explicit UI configurations injected by Pydantic (e.g. ui:widget, ui:options)
        for (const [pKey, pVal] of Object.entries(prop)) {
            if (pKey.startsWith("ui:")) {
                fieldUi[pKey] = pVal;
            }
        }

        // 2. Process dynamic dropdowns and fallbacks
        if (options[key]?.enum?.length) {
            fieldUi["ui:widget"] = "select";
            fieldUi["ui:emptyValue"] = undefined;
        } else if ((prop as any).dynamic_dropdown) {
            fieldUi["ui:disabled"] = true;
            fieldUi["ui:placeholder"] = "--- Select dependencies first or no options ---";
            fieldUi["ui:emptyValue"] = undefined;
        } else if (prop.format === "date" && !fieldUi["ui:widget"]) {
            fieldUi["ui:widget"] = "date";
            fieldUi["ui:emptyValue"] = undefined;
        } else if ((key === "description" || key === "comments") && !fieldUi["ui:widget"]) {
            fieldUi["ui:widget"] = "textarea";
            fieldUi["ui:options"] = { ...fieldUi["ui:options"], rows: 3 };
        }

        if (Object.keys(fieldUi).length > 0) {
            ui[key] = fieldUi;
        }
    }

    return ui;
}

/**
 * Custom widget to render boolean fields as a nice Radix toggle switch instead of a native checkbox.
 * Also fixes React "uncontrolled to controlled" warning by enforcing a boolean on `checked`.
 */
const CustomSwitchWidget = ({
    id,
    value,
    disabled,
    readonly,
    onChange,
}: WidgetProps) => {
    return (
        <div className="flex items-center h-9">
            <Switch
                id={id}
                checked={!!value}
                disabled={disabled || readonly}
                onCheckedChange={onChange}
            />
        </div>
    );
};

/**
 * Generic dynamic form component using React JSON Schema Form (RJSF).
 *
 * Handles:
 * - Pydantic Optional[X] → anyOf → normal input
 * - API enum data → dropdowns with human-readable labels
 * - Date fields → native date picker via format: "date"
 * - Hidden internal fields (form_meta)
 *
 * Not tied to any specific agent — works for any backend tool schema.
 */
export function DynamicToolForm({
    toolName,
    baseSchema,
    options,
    formData,
    onChange,
    onSubmit,
    onCancel,
}: DynamicToolFormProps) {
    const processedSchema = processSchema(baseSchema as RJSFSchema);
    const schema = mergeOptions(processedSchema, options);
    const uiSchema = buildUiSchema(schema, options);

    const handleChange = (newFormData: Record<string, unknown>) => {
        const updatedData = { ...newFormData };

        for (const [key, value] of Object.entries(updatedData)) {
            const propSchema = schema.properties?.[key] as any;

            if (value === "" || value === undefined || value === null) {
                delete updatedData[key];
                continue;
            }

            if (value !== formData?.[key]) {
                // Key changed, find dependents
                for (const [depKey, depProp] of Object.entries(schema.properties || {})) {
                    const dependsOn = (depProp as any).depends_on;
                    if (dependsOn) {
                        const deps = Array.isArray(dependsOn) ? dependsOn : [dependsOn];
                        if (deps.includes(key)) {
                            delete updatedData[depKey]; // Clear dependent value
                        }
                    }
                }
            }
        }

        onChange?.(updatedData);
    };

    return (
        <div className="rounded-lg border border-border bg-card p-4 shadow-sm w-full my-2">
            <h3 className="text-sm font-semibold mb-4 capitalize text-foreground">
                {toolName.replace(/_/g, " ")}
            </h3>

            <Form
                schema={schema}
                uiSchema={uiSchema}
                formData={formData}
                validator={validator}
                widgets={{ CheckboxWidget: CustomSwitchWidget, richtext: RichTextWidget }}
                transformErrors={(errors) => {
                    return errors.filter(error => {
                        if (!error.property) return true;

                        const propName = error.property.replace(/^\./, "").replace(/^\[\'?/, "").replace(/\'?\]$/, "");

                        if (error.name === "type") {
                            const val = formData?.[propName];
                            if (val === "" || val === null || val === undefined) {
                                const isRequired = schema.required?.includes(propName);
                                if (!isRequired) return false;
                            }
                        }
                        return true;
                    });
                }}
                onChange={({ formData }) => {
                    const typedData = { ...formData } as any;
                    for (const [key, value] of Object.entries(typedData)) {
                        if (schema.properties?.[key] && (schema.properties[key] as any).type === "integer" && typeof value === "string" && !isNaN(Number(value)) && value.trim() !== "") {
                            typedData[key] = parseInt(value, 10);
                        }
                    }
                    handleChange(typedData as Record<string, unknown>);
                }}
                onSubmit={({ formData }) => {
                    const cleanedData = { ...formData } as Record<string, unknown>;
                    for (const [key, value] of Object.entries(cleanedData)) {
                        if (value === "" || value === undefined || value === null) {
                            delete cleanedData[key];
                        } else if (schema.properties?.[key] && (schema.properties[key] as any).type === "integer" && typeof value === "string" && !isNaN(Number(value)) && value.trim() !== "") {
                            cleanedData[key] = parseInt(value, 10);
                        }
                    }
                    onSubmit(cleanedData);
                }}
                className="
                    [&_.form-group]:mb-4
                    [&_label.control-label]:text-sm [&_label.control-label]:font-medium [&_label.control-label]:text-foreground [&_label.control-label]:mb-1 [&_label.control-label]:block
                    [&_p.field-description]:hidden
                    [&_input[type=text]]:w-full [&_input[type=text]]:rounded-md [&_input[type=text]]:border [&_input[type=text]]:border-input [&_input[type=text]]:bg-background [&_input[type=text]]:px-3 [&_input[type=text]]:py-2 [&_input[type=text]]:text-sm [&_input[type=text]]:focus:outline-none [&_input[type=text]]:focus:ring-2 [&_input[type=text]]:focus:ring-ring
                    [&_input[type=number]]:w-full [&_input[type=number]]:rounded-md [&_input[type=number]]:border [&_input[type=number]]:border-input [&_input[type=number]]:bg-background [&_input[type=number]]:px-3 [&_input[type=number]]:py-2 [&_input[type=number]]:text-sm
                    [&_input[type=date]]:w-full [&_input[type=date]]:rounded-md [&_input[type=date]]:border [&_input[type=date]]:border-input [&_input[type=date]]:bg-background [&_input[type=date]]:px-3 [&_input[type=date]]:py-2 [&_input[type=date]]:text-sm
                    [&_textarea]:w-full [&_textarea]:rounded-md [&_textarea]:border [&_textarea]:border-input [&_textarea]:bg-background [&_textarea]:px-3 [&_textarea]:py-2 [&_textarea]:text-sm [&_textarea]:focus:outline-none [&_textarea]:focus:ring-2 [&_textarea]:focus:ring-ring [&_textarea]:resize-y
                    [&_select]:w-full [&_select]:rounded-md [&_select]:border [&_select]:border-input [&_select]:bg-background [&_select]:px-3 [&_select]:py-2 [&_select]:text-sm [&_select]:focus:outline-none [&_select]:focus:ring-2 [&_select]:focus:ring-ring
                    [&_.error-detail]:text-xs [&_.error-detail]:text-destructive [&_.error-detail]:mt-1
                "
            >
                <div className="flex gap-2 mt-6 pt-4 border-t border-border">
                    <button
                        type="submit"
                        className="px-4 py-2 text-sm font-medium rounded-md bg-foreground text-background hover:bg-foreground/90 transition-colors"
                    >
                        Submit
                    </button>
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-4 py-2 text-sm font-medium rounded-md border border-border hover:bg-muted transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </Form>
        </div>
    );
}
