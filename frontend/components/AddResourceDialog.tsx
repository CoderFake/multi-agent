import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Resource } from "@/lib/types";

interface AddResourceDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    newResource: Resource;
    setNewResource: (resource: Resource) => void;
    addResource: () => void;
}

export function AddResourceDialog({
    isOpen,
    onOpenChange,
    newResource,
    setNewResource,
    addResource,
}: AddResourceDialogProps) {
    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Add Resource</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <span className="text-right text-sm font-medium">
                            URL
                        </span>
                        <Input
                            value={newResource.url}
                            onChange={(e) =>
                                setNewResource({ ...newResource, url: e.target.value })
                            }
                            className="col-span-3"
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <span className="text-right text-sm font-medium">
                            Title
                        </span>
                        <Input
                            value={newResource.title}
                            onChange={(e) =>
                                setNewResource({ ...newResource, title: e.target.value })
                            }
                            className="col-span-3"
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <span className="text-right text-sm font-medium">
                            Description
                        </span>
                        <Textarea
                            value={newResource.description}
                            onChange={(e) =>
                                setNewResource({
                                    ...newResource,
                                    description: e.target.value,
                                })
                            }
                            className="col-span-3"
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button onClick={addResource}>Add resource</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
