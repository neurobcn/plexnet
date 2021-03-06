import py, os, sys
from py.__.test.plugin.pytest_capture import CaptureManager, EncodedFile

class TestCaptureManager:
    def test_configure_per_fspath(self, testdir):
        config = testdir.parseconfig(testdir.tmpdir)
        assert config.getvalue("capture") is None
        capman = CaptureManager()
        assert capman._getmethod(config, None) == "fd" # default

        for name in ('no', 'fd', 'sys'):
            sub = testdir.tmpdir.mkdir("dir" + name)
            sub.ensure("__init__.py")
            sub.join("conftest.py").write('option_capture = %r' % name)
            assert capman._getmethod(config, sub.join("test_hello.py")) == name

    @py.test.mark.multi(method=['no', 'fd', 'sys'])
    def test_capturing_basic_api(self, method):
        capouter = py.io.StdCaptureFD()
        old = sys.stdout, sys.stderr, sys.stdin
        try:
            capman = CaptureManager()
            capman.resumecapture(method)
            print "hello"
            out, err = capman.suspendcapture()
            if method == "no":
                assert old == (sys.stdout, sys.stderr, sys.stdin)
            else:
                assert out == "hello\n"
            capman.resumecapture(method)
            out, err = capman.suspendcapture()
            assert not out and not err 
        finally:
            capouter.reset()
      
    def test_juggle_capturings(self, testdir):
        capouter = py.io.StdCaptureFD()
        try:
            config = testdir.parseconfig(testdir.tmpdir)
            capman = CaptureManager()
            capman.resumecapture("fd")
            py.test.raises(ValueError, 'capman.resumecapture("fd")')
            py.test.raises(ValueError, 'capman.resumecapture("sys")')
            os.write(1, "hello\n")
            out, err = capman.suspendcapture()
            assert out == "hello\n"
            capman.resumecapture("sys")
            os.write(1, "hello\n")
            print >>sys.stderr, "world"
            out, err = capman.suspendcapture()
            assert not out
            assert err == "world\n"
        finally:
            capouter.reset()

@py.test.mark.multi(method=['fd', 'sys'])
def test_capturing_unicode(testdir, method):
    testdir.makepyfile("""
        # taken from issue 227 from nosetests
        def test_unicode():
            import sys
            print sys.stdout
            print u'b\\u00f6y'
    """)
    result = testdir.runpytest("--capture=%s" % method)
    result.stdout.fnmatch_lines([
        "*1 passed*"
    ])

@py.test.mark.multi(method=['fd', 'sys'])
def test_capturing_bytes_in_utf8_encoding(testdir, method):
    testdir.makepyfile("""
        def test_unicode():
            print '\\xe2'
    """)
    result = testdir.runpytest("--capture=%s" % method)
    result.stdout.fnmatch_lines([
        "*1 passed*"
    ])

def test_UnicodeFile(testdir):
    p = testdir.makepyfile("hello")
    f = p.open('w')
    pf = EncodedFile(f, "UTF-8")
    pf.write(u'b\\00f6y\n')
    pf.write('b\\00f6y\n')
    pf.close()
    assert f.closed
    lines = p.readlines()
    assert lines[0] == lines[1]

def test_collect_capturing(testdir):
    p = testdir.makepyfile("""
        print "collect %s failure" % 13
        import xyz42123
    """)
    result = testdir.runpytest(p)
    result.stdout.fnmatch_lines([
        "*Captured stdout*",
        "*collect 13 failure*", 
    ])

class TestPerTestCapturing:
    def test_capture_and_fixtures(self, testdir):
        p = testdir.makepyfile("""
            def setup_module(mod):
                print "setup module"
            def setup_function(function):
                print "setup", function.__name__
            def test_func1():
                print "in func1"
                assert 0
            def test_func2():
                print "in func2"
                assert 0
        """)
        result = testdir.runpytest(p)
        result.stdout.fnmatch_lines([
            "setup module*",
            "setup test_func1*",
            "in func1*",
            "setup test_func2*",
            "in func2*", 
        ]) 

    @py.test.mark.xfail
    def test_capture_scope_cache(self, testdir):
        p = testdir.makepyfile("""
            import sys
            def setup_module(func):
                print "module-setup"
            def setup_function(func):
                print "function-setup"
            def test_func():
                print "in function"
                assert 0
            def teardown_function(func):
                print "in teardown"
        """)
        result = testdir.runpytest(p)
        result.stdout.fnmatch_lines([
            "*test_func():*",
            "*Captured stdout during setup*", 
            "module-setup*", 
            "function-setup*", 
            "*Captured stdout*",
            "in teardown*",
        ])


    def test_no_carry_over(self, testdir):
        p = testdir.makepyfile("""
            def test_func1():
                print "in func1"
            def test_func2():
                print "in func2"
                assert 0
        """)
        result = testdir.runpytest(p)
        s = result.stdout.str()
        assert "in func1" not in s 
        assert "in func2" in s 


    def test_teardown_capturing(self, testdir):
        p = testdir.makepyfile("""
            def setup_function(function):
                print "setup func1"
            def teardown_function(function):
                print "teardown func1"
                assert 0
            def test_func1(): 
                print "in func1"
                pass
        """)
        result = testdir.runpytest(p)
        assert result.stdout.fnmatch_lines([
            '*teardown_function*',
            '*Captured stdout*',
            "setup func1*",
            "in func1*",
            "teardown func1*",
            #"*1 fixture failure*"
        ])

    def test_teardown_final_capturing(self, testdir):
        p = testdir.makepyfile("""
            def teardown_module(mod):
                print "teardown module"
                assert 0
            def test_func():
                pass
        """)
        result = testdir.runpytest(p)
        assert result.stdout.fnmatch_lines([
            "*def teardown_module(mod):*", 
            "*Captured stdout*", 
            "*teardown module*", 
            "*1 error*", 
        ])

    def test_capturing_outerr(self, testdir): 
        p1 = testdir.makepyfile("""
            import sys 
            def test_capturing():
                print 42
                print >>sys.stderr, 23 
            def test_capturing_error():
                print 1
                print >>sys.stderr, 2
                raise ValueError
        """)
        result = testdir.runpytest(p1)
        result.stdout.fnmatch_lines([
            "*test_capturing_outerr.py .F", 
            "====* FAILURES *====",
            "____*____", 
            "*test_capturing_outerr.py:8: ValueError",
            "*--- Captured stdout ---*",
            "1",
            "*--- Captured stderr ---*",
            "2",
        ])

class TestLoggingInteraction:
    def test_logging_stream_ownership(self, testdir):
        p = testdir.makepyfile("""
            def test_logging():
                import logging
                import StringIO
                stream = StringIO.StringIO()
                logging.basicConfig(stream=stream)
                stream.close() # to free memory/release resources
        """)
        result = testdir.runpytest(p)
        result.stderr.str().find("atexit") == -1

    def test_capturing_and_logging_fundamentals(self, testdir):
        # here we check a fundamental feature 
        rootdir = str(py.path.local(py.__file__).dirpath().dirpath())
        p = testdir.makepyfile("""
            import sys
            sys.path.insert(0, %r)
            import py, logging
            cap = py.io.StdCaptureFD(out=False, in_=False)
            logging.warn("hello1")
            outerr = cap.suspend()

            print "suspeneded and captured", outerr

            logging.warn("hello2")

            cap.resume()
            logging.warn("hello3")

            outerr = cap.suspend()
            print "suspend2 and captured", outerr
        """ % rootdir)
        result = testdir.runpython(p)
        assert result.stdout.fnmatch_lines([
            "suspeneded and captured*hello1*",
            "suspend2 and captured*hello2*WARNING:root:hello3*",
        ])
        assert "atexit" not in result.stderr.str()
        
           
    def test_logging_and_immediate_setupteardown(self, testdir):
        p = testdir.makepyfile("""
            import logging
            def setup_function(function):
                logging.warn("hello1")

            def test_logging():
                logging.warn("hello2")
                assert 0

            def teardown_function(function):
                logging.warn("hello3")
                assert 0
        """)
        for optargs in (('--capture=sys',), ('--capture=fd',)):
            print optargs
            result = testdir.runpytest(p, *optargs)
            s = result.stdout.str()
            result.stdout.fnmatch_lines([
                "*WARN*hello3",  # errors show first!
                "*WARN*hello1", 
                "*WARN*hello2", 
            ])
            # verify proper termination
            assert "closed" not in s

    def test_logging_and_crossscope_fixtures(self, testdir):
        p = testdir.makepyfile("""
            import logging
            def setup_module(function):
                logging.warn("hello1")

            def test_logging():
                logging.warn("hello2")
                assert 0

            def teardown_module(function):
                logging.warn("hello3")
                assert 0
        """)
        for optargs in (('--capture=sys',), ('--capture=fd',)):
            print optargs
            result = testdir.runpytest(p, *optargs)
            s = result.stdout.str()
            result.stdout.fnmatch_lines([
                "*WARN*hello3",  # errors come first
                "*WARN*hello1", 
                "*WARN*hello2", 
            ])
            # verify proper termination
            assert "closed" not in s

class TestCaptureFuncarg:
    def test_std_functional(self, testdir):        
        reprec = testdir.inline_runsource("""
            def test_hello(capsys):
                print 42
                out, err = capsys.readouterr()
                assert out.startswith("42")
        """)
        reprec.assertoutcome(passed=1)
        
    def test_stdfd_functional(self, testdir):        
        reprec = testdir.inline_runsource("""
            def test_hello(capfd):
                import os
                os.write(1, "42")
                out, err = capfd.readouterr()
                assert out.startswith("42")
                capfd.close()
        """)
        reprec.assertoutcome(passed=1)

    def test_partial_setup_failure(self, testdir):        
        p = testdir.makepyfile("""
            def test_hello(capfd, missingarg):
                pass
        """)
        result = testdir.runpytest(p)
        assert result.stdout.fnmatch_lines([
            "*test_partial_setup_failure*",
            "*1 error*",
        ])

    def test_keyboardinterrupt_disables_capturing(self, testdir):        
        p = testdir.makepyfile("""
            def test_hello(capfd):
                import os
                os.write(1, "42")
                raise KeyboardInterrupt()
        """)
        result = testdir.runpytest(p)
        result.stdout.fnmatch_lines([
            "*KEYBOARD INTERRUPT*"
        ])
        assert result.ret == 2

