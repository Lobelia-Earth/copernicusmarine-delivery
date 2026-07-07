import sys
from pathlib import Path

from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Log,
    TextArea,
)
from textual.widgets.tree import TreeNode

from pusher.core_functions.core_functions import delivery
from pusher.core_functions.models import OperationNames


class SelectableDirectoryTree(DirectoryTree):
    """DirectoryTree that highlights files toggled into a selection set."""

    def __init__(self, *args, selected: set[str], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.selected = selected

    def render_label(self, node: TreeNode, base_style: Style, style: Style) -> Text:
        label = super().render_label(node, base_style, style)
        path = node.data.path if node.data else None
        if path is not None and str(path) in self.selected:
            label.stylize("reverse bold")
        return label


class MarineProducerApp(App):
    """Prototype dual-pane file transfer UI"""

    CSS = """
    Screen > Horizontal {
        height: auto;
    }
    #panes {
        height: 1fr;
    }
    #panes > Vertical {
        width: 1fr;
        height: 100%;
        border: solid $primary;
    }
    Horizontal > Input {
        width: 1fr;
    }
    #local-tree, #remote-paths {
        height: 1fr !important;
    }
    Log {
        height: auto;
        max-height: 8;
    }
    #begin-delivery {
        margin-left: 4;
    }
    #button-group {
        width: auto;
        height: auto;
    }
    #button-group Horizontal {
        width: auto;
        height: auto;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, local_dir: Path, tree_root: Path | None = None) -> None:
        super().__init__()
        self.local_dir = local_dir
        self.tree_root = tree_root or Path(local_dir.resolve().anchor)
        self.operations: list[tuple[OperationNames, list[str]]] = []
        self.pending_uploads: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Input(placeholder="pushing entity id", id="pushing-entity-id")
            yield Input(placeholder="product id", id="product-id")
            yield Input(placeholder="dataset id", id="dataset-id")
        with Horizontal(id="panes"):
            with Vertical():
                yield Label(f"Local: {self.local_dir} (click a file to toggle queue)")
                yield SelectableDirectoryTree(
                    str(self.tree_root), selected=self.pending_uploads, id="local-tree"
                )
                yield Label("queued: (none)", id="pending-uploads")
            with Vertical():
                yield Label("Remote files to delete (one path per line)")
                yield TextArea(id="remote-paths")
        with Horizontal():
            with Vertical(id="button-group"):
                with Horizontal():
                    yield Button("Append Upload", id="append-upload")
                    yield Button("Append Delete", id="append-delete")
                yield Button("Clear Queue", id="clear-queue")
            yield Button("Begin Delivery", id="begin-delivery", disabled=True)
        yield Log()
        yield Footer()

    def _update_pending_uploads_label(self) -> None:
        label = self.query_one("#pending-uploads", Label)
        if self.pending_uploads:
            label.update("queued: " + ", ".join(sorted(self.pending_uploads)))
        else:
            label.update("queued: (none)")

    def _update_begin_delivery_state(self) -> None:
        ids_filled = all(
            self.query_one(f"#{id_}", Input).value.strip()
            for id_ in ("pushing-entity-id", "product-id", "dataset-id")
        )
        self.query_one("#begin-delivery", Button).disabled = not (
            ids_filled and self.operations
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_begin_delivery_state()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        path = str(event.path)
        if path in self.pending_uploads:
            self.pending_uploads.discard(path)
        else:
            self.pending_uploads.add(path)
        self.query_one("#local-tree", SelectableDirectoryTree).refresh()
        self._update_pending_uploads_label()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        remote_paths = self.query_one("#remote-paths", TextArea)
        log = self.query_one(Log)
        if event.button.id == "append-upload":
            files = sorted(self.pending_uploads)
            if files:
                self.operations.append(("upload", files))
                self.pending_uploads.clear()
                self.query_one("#local-tree", SelectableDirectoryTree).refresh()
                self._update_pending_uploads_label()
                log.write_line(f"queued upload: {files}")
            else:
                log.write_line("No files added to upload")
        elif event.button.id == "clear-queue":
            self.operations.clear()
            self.pending_uploads.clear()
            remote_paths.clear()
            self.query_one("#local-tree", SelectableDirectoryTree).refresh()
            self._update_pending_uploads_label()
            log.write_line("cleared queue")
        elif event.button.id == "append-delete":
            files = [
                line.strip() for line in remote_paths.text.splitlines() if line.strip()
            ]
            if files:
                self.operations.append(("delete", files))
                remote_paths.clear()
                log.write_line(f"queued delete: {files}")
            else:
                log.write_line("No files added to delete")
        elif event.button.id == "begin-delivery":
            log.write_line(f"begin delivery with operations: {self.operations}")
            self.run_worker(
                lambda: self._run_delivery(
                    self.operations,
                    self.query_one("#pushing-entity-id", Input).value.strip(),
                    self.query_one("#product-id", Input).value.strip(),
                    self.query_one("#dataset-id", Input).value.strip(),
                ),
                thread=True,
            )
            return
        self._update_begin_delivery_state()

    def _run_delivery(
        self,
        operations: list[tuple[OperationNames, list[str]]],
        pushing_entity_id: str,
        product_id: str,
        dataset_id: str,
    ) -> None:
        response, manifest = delivery(
            operations=operations,
            pushing_entity_id=pushing_entity_id,
            product_id=product_id,
            dataset_id=dataset_id,
        )
        log = self.query_one(Log)
        if response.fatal_error:
            self.call_from_thread(log.write_line, f"FATAL: {response.fatal_error}")
        else:
            self.call_from_thread(
                log.write_line, f"delivery id: {response.delivery_id}"
            )


if __name__ == "__main__":
    cli_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    local_dir = cli_dir or Path.cwd()
    MarineProducerApp(local_dir, tree_root=cli_dir).run()
