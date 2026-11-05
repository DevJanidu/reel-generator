// DEVELOPMENT-built compatibility launcher. No shell, arbitrary code or model commands.
// Remotion 4 uses filter-script options removed by FFmpeg 9. Translate them to direct filters.
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
class FfmpegCompat {
  [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] struct Startup {
    public int cb; public string reserved,desktop,title; public int x,y,xsize,ysize,xchars,ychars,fill,flags;
    public short show,reserved2; public IntPtr reservedPtr,input,output,error;
  }
  [StructLayout(LayoutKind.Sequential)] struct ProcessInfo {public IntPtr process,thread; public int pid,tid;}
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcessW(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string cwd,ref Startup si,out ProcessInfo pi);
  [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int which);
  [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr handle,uint ms);
  [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr handle,out uint code);
  [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
  static string Quote(string arg) {
    var b=new StringBuilder("\"");int slashes=0;
    foreach(char c in arg){if(c=='\\'){slashes++;continue;}if(c=='"'){b.Append('\\',slashes*2+1);b.Append(c);slashes=0;continue;}b.Append('\\',slashes);slashes=0;b.Append(c);}
    b.Append('\\',slashes*2);b.Append('"');return b.ToString();
  }
  static int Main(string[] args) {
    try {
      string exe=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"ffmpeg-native.exe");
      var translated=new List<string>();
      for(int i=0;i<args.Length;i++) {
        if(args[i]=="-filter_complex_script" || args[i]=="-filter_script:a") {
          string option=args[i]=="-filter_complex_script"?"-filter_complex":"-filter:a";
          if(++i>=args.Length)throw new ArgumentException("Missing filter-script path");
          translated.Add(option);translated.Add(File.ReadAllText(args[i]));
        } else if(args[i]=="libfdk_aac") translated.Add("aac");
        else translated.Add(args[i]);
      }
      var cmd=new StringBuilder(Quote(exe));foreach(string arg in translated)cmd.Append(" ").Append(Quote(arg));
      var si=new Startup();si.cb=Marshal.SizeOf(typeof(Startup));si.flags=0x100;
      si.input=GetStdHandle(-10);si.output=GetStdHandle(-11);si.error=GetStdHandle(-12);
      ProcessInfo pi;
      if(!CreateProcessW(exe,cmd,IntPtr.Zero,IntPtr.Zero,true,0,IntPtr.Zero,null,ref si,out pi))throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
      WaitForSingleObject(pi.process,0xffffffff);uint code;GetExitCodeProcess(pi.process,out code);CloseHandle(pi.thread);CloseHandle(pi.process);
      return unchecked((int)code);
    } catch(Exception e){Console.Error.WriteLine("FFmpeg compatibility launcher: "+e.Message);return 1;}
  }
}
