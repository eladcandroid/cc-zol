import json
import pytest
from providers.generic import GenericOpenAIProvider
from providers.base import ProviderConfig
from providers.common.sse_builder import SSEBuilder


@pytest.mark.asyncio
async def test_task_tool_interception():
    """Test that Task tool's run_in_background is forced to False."""
    # Setup provider
    config = ProviderConfig(api_key="test")
    provider = GenericOpenAIProvider(config)

    # Use real SSEBuilder
    sse = SSEBuilder("msg_test", "test-model", input_tokens=0)

    # Tool call data (Task tool) - first chunk with name
    tc_name = {
        "index": 0,
        "id": "tool_123",
        "function": {
            "name": "Task",
            "arguments": "",
        },
    }

    # Process name chunk (starts the tool block)
    events = list(provider._process_tool_call(tc_name, sse))

    # Now send the arguments as a complete JSON string
    tc_args = {
        "index": 0,
        "id": None,
        "function": {
            "name": None,
            "arguments": json.dumps(
                {
                    "description": "test task",
                    "prompt": "do something",
                    "run_in_background": True,
                }
            ),
        },
    }

    events2 = list(provider._process_tool_call(tc_args, sse))

    # The buffer_task_args method should have returned the patched args.
    # Find emitted tool delta events that contain JSON
    all_events = events + events2
    tool_delta_events = [e for e in all_events if "input_json_delta" in e]

    assert len(tool_delta_events) > 0, f"No tool delta events found in: {all_events}"

    # Parse the emitted JSON to verify run_in_background was forced to False
    for event_str in tool_delta_events:
        for line in event_str.splitlines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if "delta" in data and "partial_json" in data["delta"]:
                    args_json = json.loads(data["delta"]["partial_json"])
                    assert args_json["run_in_background"] is False, (
                        f"run_in_background was not forced to False: {args_json}"
                    )
                    print("Verification successful: run_in_background was forced to False")
                    return

    # If we get here, check if the args were flushed instead
    flush_events = list(provider._flush_task_arg_buffers(sse))
    for event_str in flush_events:
        for line in event_str.splitlines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if "delta" in data and "partial_json" in data["delta"]:
                    args_json = json.loads(data["delta"]["partial_json"])
                    assert args_json["run_in_background"] is False
                    print("Verification successful: run_in_background was forced to False (via flush)")
                    return

    pytest.fail("Could not find emitted Task tool args in any event")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_task_tool_interception())
