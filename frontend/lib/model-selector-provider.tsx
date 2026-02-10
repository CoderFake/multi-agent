"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

interface ModelSelectorContextType {
    model: string;
    setModel: (model: string) => void;
    agent: string;
    setAgent: (agent: string) => void;
}

const ModelSelectorContext = createContext<ModelSelectorContextType | undefined>(
    undefined
);

export function ModelSelectorProvider({ children }: { children: ReactNode }) {
    const [model, setModel] = useState("gpt-4-turbo-preview");
    const [agent, setAgent] = useState("default");

    return (
        <ModelSelectorContext.Provider value={{ model, setModel, agent, setAgent }}>
            {children}
        </ModelSelectorContext.Provider>
    );
}

export function useModelSelectorContext() {
    const context = useContext(ModelSelectorContext);
    if (context === undefined) {
        // Return defaults so it works even without the provider wrapper
        return {
            model: "gpt-4-turbo-preview",
            setModel: () => { },
            agent: "default",
            setAgent: () => { },
        };
    }
    return context;
}
