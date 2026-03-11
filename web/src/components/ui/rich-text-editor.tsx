"use client";

import dynamic from "next/dynamic";
import "react-quill-new/dist/quill.snow.css";

// Dynamically import ReactQuill to avoid SSR issues with window/document
const ReactQuill = dynamic(() => import("react-quill-new"), { ssr: false });

export interface RichTextEditorProps {
    id?: string;
    value?: string;
    onChange?: (value: string) => void;
    placeholder?: string;
    disabled?: boolean;
    readonly?: boolean;
    onBlur?: (id: string, value: string) => void;
    onFocus?: (id: string, value: string) => void;
}

export function RichTextEditor({
    id = "rich-text",
    value,
    onChange,
    placeholder = "Supports rich text...",
    disabled,
    readonly,
    onBlur,
    onFocus,
}: RichTextEditorProps) {
    return (
        <div className="rich-text-container w-full [&_.ql-container]:min-h-[150px] [&_.ql-container]:text-sm [&_.ql-editor]:min-h-[150px] [&_.ql-toolbar]:rounded-t-md [&_.ql-toolbar]:border-input [&_.ql-container]:rounded-b-md [&_.ql-container]:border-input">
            <ReactQuill
                theme="snow"
                value={value || ""}
                onChange={onChange as any}
                placeholder={placeholder}
                readOnly={disabled || readonly}
                onBlur={(_range: any, _source: any, editor: any) => onBlur?.(id, editor.getHTML())}
                onFocus={(_range: any, _source: any, editor: any) => onFocus?.(id, editor.getHTML())}
                modules={{
                    toolbar: [
                        [{ 'header': [1, 2, 3, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                        ['link', 'code-block'],
                        ['clean']
                    ]
                }}
            />
        </div>
    );
}

// Widget adapter for RJSF
export const RichTextWidget = ({
    id,
    value,
    disabled,
    readonly,
    onChange,
    onBlur,
    onFocus,
}: any) => {
    return (
        <RichTextEditor
            id={id}
            value={value}
            disabled={disabled}
            readonly={readonly}
            onChange={onChange}
            onBlur={onBlur}
            onFocus={onFocus}
        />
    );
};
