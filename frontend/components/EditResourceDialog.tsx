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

interface EditResourceDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    editResource: Resource | null;
    setEditResource: (resource: Resource | null) => void;
    updateResource: () => void;
}

export function EditResourceDialog({
    isOpen,
    onOpenChange,
    editResource,
    setEditResource,
    updateResource,
}: EditResourceDialogProps) {
    if (!editResource) return null;

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Edit Resource</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <span className="text-right text-sm font-medium">
                            URL
                        </span>
                        <Input
                            value={editResource.url}
                            onChange={(e) =>
                                setEditResource({ ...editResource, url: e.target.value })
                            }
                            className="col-span-3"
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <span className="text-right text-sm font-medium">
                            Title
                        </span>
                        <Input
                            value={editResource.title}
                            onChange={(e) =>
                                setEditResource({ ...editResource, title: e.target.value })
                            }
                            className="col-span-3"
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <span className="text-right text-sm font-medium">
                            Description
                        </span>
                        <Textarea
                            value={editResource.description}
                            onChange={(e) =>
                                setEditResource({
                                    ...editResource,
                                    description: e.target.value,
                                })
                            }
                            className="col-span-3"
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button onClick={updateResource}>Save changes</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
