// dietverse VR client: talks only to the dietverse backend. No model key or cloud credential is in the client.
// Attach to a GameObject with an AudioSource. Set backendUrl in the inspector (for example http://127.0.0.1:8000).
using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class BackendClient : MonoBehaviour
{
    [Tooltip("Base URL of the dietverse backend")]
    public string backendUrl = "http://127.0.0.1:8000";

    [Tooltip("Optional bearer token (DIETVERSE_API_TOKEN on the backend). Use a per-device token, not a provider key.")]
    public string apiToken = "";

    public AudioSource voice;

    private string sessionId;
    private bool busy;

    [Serializable] private class SessionReply { public string session_id; }
    [Serializable] private class ChatRequest { public string session_id; public string message; public bool speak; }
    [Serializable] private class ChatReply { public string text; public string status; public string audio_url; }

    public event Action<string> OnAnswer;
    public event Action<string> OnError;

    private UnityWebRequest Post(string path, string json)
    {
        var req = new UnityWebRequest(backendUrl.TrimEnd('/') + path, "POST");
        req.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json ?? "{}"));
        req.downloadHandler = new DownloadHandlerBuffer();
        req.SetRequestHeader("Content-Type", "application/json");
        if (!string.IsNullOrEmpty(apiToken)) req.SetRequestHeader("Authorization", "Bearer " + apiToken);
        req.timeout = 30;
        return req;
    }

    // One request at a time: the next question waits until the answer and its audio are done.
    public void Ask(string message)
    {
        if (busy) { OnError?.Invoke("Please wait for the current answer."); return; }
        StartCoroutine(AskRoutine(message));
    }

    private IEnumerator AskRoutine(string message)
    {
        busy = true;
        if (string.IsNullOrEmpty(sessionId))
        {
            using (var s = Post("/api/session", "{}"))
            {
                yield return s.SendWebRequest();
                if (s.result != UnityWebRequest.Result.Success) { Fail(s.error); yield break; }
                sessionId = JsonUtility.FromJson<SessionReply>(s.downloadHandler.text).session_id;
            }
        }
        var body = JsonUtility.ToJson(new ChatRequest { session_id = sessionId, message = message, speak = true });
        ChatReply reply;
        using (var c = Post("/api/chat", body))
        {
            yield return c.SendWebRequest();
            if (c.result != UnityWebRequest.Result.Success) { Fail(c.error); yield break; }
            reply = JsonUtility.FromJson<ChatReply>(c.downloadHandler.text);
        }
        OnAnswer?.Invoke(reply.text);
        if (!string.IsNullOrEmpty(reply.audio_url) && voice != null)
        {
            // Each answer has its own audio file on the backend, so two answers never overwrite each other.
            var type = reply.audio_url.EndsWith(".wav") ? AudioType.WAV : AudioType.MPEG;
            using (var a = UnityWebRequestMultimedia.GetAudioClip(backendUrl.TrimEnd('/') + reply.audio_url, type))
            {
                if (!string.IsNullOrEmpty(apiToken)) a.SetRequestHeader("Authorization", "Bearer " + apiToken);
                yield return a.SendWebRequest();
                if (a.result != UnityWebRequest.Result.Success) { Fail(a.error); yield break; }
                voice.Stop();
                voice.clip = DownloadHandlerAudioClip.GetContent(a);
                voice.Play();
            }
        }
        busy = false;
    }

    private void Fail(string error)
    {
        busy = false;
        Debug.LogWarning("dietverse backend: " + error);
        OnError?.Invoke("The assistant is not available now.");
    }
}
