import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Log,
    SelectionList,
    TextArea,
)

from pusher.core_functions.core_functions import delivery
from pusher.core_functions.models import OperationNames


class MarineProducerApp(App):
    """Prototype dual-pane file transfer UI"""

    CSS = """
    Screen > Horizontal {
        height: auto;
    }
    #panes {
        height: 1fr;
    }
    Horizontal > Vertical {
        width: 1fr;
        height: 100%;
        border: solid $primary;
    }
    Horizontal > Input {
        width: 1fr;
    }
    #local-list, #remote-paths {
        height: 1fr !important;
    }
    Log {
        height: auto;
        max-height: 8;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, local_dir: Path) -> None:
        super().__init__()
        self.local_dir = local_dir
        self.operations: list[tuple[OperationNames, list[str]]] = []

    def compose(self) -> ComposeResult:
        local_files = sorted(p.name for p in self.local_dir.iterdir() if p.is_file())
        yield Header()
        with Horizontal():
            yield Input(placeholder="pushing entity id", id="pushing-entity-id")
            yield Input(placeholder="product id", id="product-id")
            yield Input(placeholder="dataset id", id="dataset-id")
        with Horizontal(id="panes"):
            with Vertical():
                yield Label(f"Local: {self.local_dir}")
                yield SelectionList[str](
                    *[(name, name) for name in local_files], id="local-list"
                )
            with Vertical():
                yield Label("Remote files to delete (one path per line)")
                yield TextArea(id="remote-paths")
        with Horizontal():
            yield Button("Append Upload", id="append-upload")
            yield Button("Append Delete", id="append-delete")
            yield Button("Begin Delivery", id="begin-delivery", disabled=True)
        yield Log()
        yield Footer()

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        local_list = self.query_one("#local-list", SelectionList)
        remote_paths = self.query_one("#remote-paths", TextArea)
        log = self.query_one(Log)
        if event.button.id == "append-upload":
            files = list(local_list.selected)
            self.operations.append(("upload", files))
            local_list.deselect_all()
            log.write_line(f"queued upload: {files}")
        elif event.button.id == "append-delete":
            files = [
                line.strip() for line in remote_paths.text.splitlines() if line.strip()
            ]
            self.operations.append(("delete", files))
            remote_paths.clear()
            log.write_line(f"queued delete: {files}")
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
    local_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    MarineProducerApp(local_dir).run()
